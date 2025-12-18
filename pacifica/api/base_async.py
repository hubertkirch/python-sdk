"""
Async Base API client for Pacifica - Optimized for parallel execution
"""

import aiohttp
import asyncio
import time
from typing import Dict, Optional, Any, List
from urllib.parse import urljoin
import logging
import json
from ..exceptions import (
    PacificaAPIError,
    PacificaAccountNotFoundError,
    PacificaBetaAccessError
)


logger = logging.getLogger(__name__)


class BaseAsyncAPIClient:
    """Async base HTTP client for Pacifica API with parallel execution support"""

    MAINNET_API = "https://api.pacifica.fi"
    TESTNET_API = "https://test-api.pacifica.fi"

    def __init__(
        self,
        auth=None,
        base_url: Optional[str] = None,
        testnet: bool = False,
        timeout: int = 30,
        max_connections: int = 100,
        max_per_host: int = 30
    ):
        """
        Initialize async base API client.

        Args:
            auth: PacificaAuth instance
            base_url: Override base URL
            testnet: Use testnet API
            timeout: Request timeout in seconds
            max_connections: Maximum total connections
            max_per_host: Maximum connections per host
        """
        self.auth = auth
        self.timeout = aiohttp.ClientTimeout(total=timeout)

        if base_url:
            self.base_url = base_url
        elif testnet:
            self.base_url = self.TESTNET_API
        else:
            self.base_url = self.MAINNET_API

        # Configure connection pooling for optimal performance
        self.connector = aiohttp.TCPConnector(
            limit=max_connections,
            limit_per_host=max_per_host,
            ttl_dns_cache=300,
            enable_cleanup_closed=True
        )

        self.session = None
        self._headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            connector=self.connector,
            timeout=self.timeout,
            headers=self._headers
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    async def ensure_session(self):
        """Ensure session is created for non-context usage"""
        if not self.session:
            self.session = aiohttp.ClientSession(
                connector=self.connector,
                timeout=self.timeout,
                headers=self._headers
            )

    async def close(self):
        """Close the session"""
        if self.session:
            await self.session.close()

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        authenticated: bool = False,
        additional_headers: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Make an async API request.

        Args:
            method: HTTP method
            endpoint: API endpoint
            params: Query parameters
            data: Request body
            authenticated: Whether request needs authentication
            additional_headers: Additional headers

        Returns:
            API response data

        Raises:
            PacificaAPIError: On API errors
        """
        await self.ensure_session()

        url = urljoin(self.base_url, endpoint)

        headers = {}
        if authenticated and self.auth:
            auth_headers = self.auth.get_auth_headers()
            headers.update(auth_headers)

        if additional_headers:
            headers.update(additional_headers)

        if self.auth and params is None:
            params = {}
        if self.auth and params and "account" not in params:
            params["account"] = self.auth.get_account()

        logger.debug(f"{method} {url} params={params}")

        try:
            async with self.session.request(
                method,
                url,
                params=params,
                json=data,
                headers=headers
            ) as response:
                if response.status == 404:
                    if "account" in str(response.url):
                        account = params.get("account", "unknown")
                        raise PacificaAccountNotFoundError(account)

                if response.status == 403:
                    error_data = await response.json()
                    if "beta" in error_data.get("msg", "").lower():
                        raise PacificaBetaAccessError(error_data.get("msg"))

                if response.status >= 400:
                    try:
                        error_data = await response.json()
                        message = error_data.get("msg", await response.text())
                    except:
                        message = await response.text()
                    raise PacificaAPIError(response.status, message)

                result = await response.json()
                if not result.get("success", True):
                    raise PacificaAPIError(
                        response.status,
                        result.get("msg", "Request failed"),
                        result
                    )

                return result

        except aiohttp.ClientError as e:
            logger.error(f"Request failed: {e}")
            raise PacificaAPIError(500, str(e))

    async def get(self, endpoint: str, params: Optional[Dict] = None, authenticated: bool = False) -> Dict:
        """Async GET request"""
        return await self._request("GET", endpoint, params=params, authenticated=authenticated)

    async def post(self, endpoint: str, data: Optional[Dict] = None, authenticated: bool = True, headers: Optional[Dict] = None) -> Dict:
        """Async POST request with optional headers"""
        return await self._request("POST", endpoint, data=data, authenticated=authenticated, additional_headers=headers)

    async def delete(self, endpoint: str, params: Optional[Dict] = None, authenticated: bool = True) -> Dict:
        """Async DELETE request"""
        return await self._request("DELETE", endpoint, params=params, authenticated=authenticated)

    def _build_request_with_auth(self, data: Dict, signature_type: str = "create_order") -> Dict:
        """
        Build a request with proper authentication fields.
        Same as sync version for compatibility.
        """
        if not self.auth:
            return data

        timestamp = int(time.time() * 1000)

        signature_header = {
            "timestamp": timestamp,
            "expiry_window": 5000,
            "type": signature_type
        }

        _, signature = self.auth.sign_message(signature_header, data)

        request = {
            "account": self.auth.get_account(),
            "signature": signature,
            "timestamp": timestamp,
            "expiry_window": 5000,
            **data
        }

        if self.auth.is_agent_mode():
            request["agent_wallet"] = self.auth.get_agent_wallet()
        else:
            request["agent_wallet"] = None

        return request

    async def gather_with_errors(self, *tasks, return_exceptions=True):
        """
        Gather multiple tasks and handle errors gracefully.

        Args:
            *tasks: Variable number of async tasks
            return_exceptions: If True, exceptions are returned as results

        Returns:
            List of results (or exceptions if return_exceptions=True)
        """
        return await asyncio.gather(*tasks, return_exceptions=return_exceptions)

    async def execute_parallel(self, requests: List[Dict]) -> List[Any]:
        """
        Execute multiple requests in parallel.

        Args:
            requests: List of request dictionaries with keys:
                - method: HTTP method
                - endpoint: API endpoint
                - params: Optional query params
                - data: Optional request body
                - authenticated: Optional auth flag

        Returns:
            List of responses in the same order as requests
        """
        tasks = []
        for req in requests:
            method = req.get("method", "GET")
            endpoint = req["endpoint"]
            params = req.get("params")
            data = req.get("data")
            authenticated = req.get("authenticated", False)

            if method == "GET":
                task = self.get(endpoint, params, authenticated)
            elif method == "POST":
                task = self.post(endpoint, data, authenticated)
            elif method == "DELETE":
                task = self.delete(endpoint, params, authenticated)
            else:
                raise ValueError(f"Unsupported method: {method}")

            tasks.append(task)

        return await self.gather_with_errors(*tasks)

    async def retry_with_backoff(
        self,
        func,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0
    ):
        """
        Retry a function with exponential backoff.

        Args:
            func: Async function to retry
            max_retries: Maximum number of retries
            base_delay: Initial delay between retries
            max_delay: Maximum delay between retries

        Returns:
            Result from successful function call

        Raises:
            Last exception if all retries fail
        """
        last_exception = None

        for attempt in range(max_retries):
            try:
                return await func()
            except Exception as e:
                last_exception = e
                if attempt < max_retries - 1:
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"All {max_retries} attempts failed")

        raise last_exception