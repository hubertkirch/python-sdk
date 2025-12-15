"""
Base API client for Pacifica
"""

import requests
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


class BaseAPIClient:
    """Base HTTP client for Pacifica API"""

    MAINNET_API = "https://api.pacifica.fi"
    TESTNET_API = "https://test-api.pacifica.fi"

    def __init__(
        self,
        auth=None,
        base_url: Optional[str] = None,
        testnet: bool = False,
        timeout: int = 30
    ):
        """
        Initialize base API client.

        Args:
            auth: PacificaAuth instance
            base_url: Override base URL
            testnet: Use testnet API
            timeout: Request timeout in seconds
        """
        self.auth = auth
        self.timeout = timeout

        if base_url:
            self.base_url = base_url
        elif testnet:
            self.base_url = self.TESTNET_API
        else:
            self.base_url = self.MAINNET_API

        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json"
        })

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        authenticated: bool = False,
        additional_headers: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Make an API request.

        Args:
            method: HTTP method
            endpoint: API endpoint
            params: Query parameters
            data: Request body
            authenticated: Whether request needs authentication

        Returns:
            API response data

        Raises:
            PacificaAPIError: On API errors
            PacificaAccountNotFoundError: When account has no trading history
            PacificaBetaAccessError: When beta access is required
        """
        url = urljoin(self.base_url, endpoint)

        headers = {}
        if authenticated and self.auth:
            auth_headers = self.auth.get_auth_headers()
            headers.update(auth_headers)

        if additional_headers:
            headers.update(additional_headers)

        if self.auth and params is None:
            params = {}
        if self.auth and "account" not in params:
            params["account"] = self.auth.get_account()  # Use get_account() for agent mode support

        logger.debug(f"{method} {url} params={params}")

        try:
            response = self.session.request(
                method,
                url,
                params=params,
                json=data,
                headers=headers,
                timeout=self.timeout
            )

            if response.status_code == 404:
                if "account" in str(response.url):
                    account = params.get("account", "unknown")
                    raise PacificaAccountNotFoundError(account)

            if response.status_code == 403:
                error_data = response.json()
                if "beta" in error_data.get("msg", "").lower():
                    raise PacificaBetaAccessError(error_data.get("msg"))

            if response.status_code >= 400:
                try:
                    error_data = response.json()
                    message = error_data.get("msg", response.text)
                except:
                    message = response.text
                raise PacificaAPIError(response.status_code, message)

            result = response.json()
            if not result.get("success", True):
                raise PacificaAPIError(
                    response.status_code,
                    result.get("msg", "Request failed"),
                    result
                )

            return result

        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise PacificaAPIError(500, str(e))

    def get(self, endpoint: str, params: Optional[Dict] = None, authenticated: bool = False) -> Dict:
        """GET request"""
        return self._request("GET", endpoint, params=params, authenticated=authenticated)

    def post(self, endpoint: str, data: Optional[Dict] = None, authenticated: bool = True, headers: Optional[Dict] = None) -> Dict:
        """POST request with optional headers"""
        return self._request("POST", endpoint, data=data, authenticated=authenticated, additional_headers=headers)

    def delete(self, endpoint: str, params: Optional[Dict] = None, authenticated: bool = True) -> Dict:
        """DELETE request"""
        return self._request("DELETE", endpoint, params=params, authenticated=authenticated)

    def _build_request_with_auth(self, data: Dict, signature_type: str = "create_order") -> Dict:
        """
        Build a request with proper authentication fields.
        Handles both direct account and agent key modes.

        Args:
            data: The data to sign
            signature_type: Type field for signature header

        Returns:
            Dict with proper authentication fields including agent_wallet if needed
        """
        if not self.auth:
            return data

        timestamp = int(time.time() * 1000)

        # Prepare signature header
        signature_header = {
            "timestamp": timestamp,
            "expiry_window": 5000,
            "type": signature_type
        }

        # Sign the payload
        _, signature = self.auth.sign_message(signature_header, data)

        # Build request with correct fields
        request = {
            "account": self.auth.get_account(),  # Main account or own account
            "signature": signature,
            "timestamp": timestamp,
            "expiry_window": 5000,
            **data
        }

        # Add agent_wallet field if in agent mode
        if self.auth.is_agent_mode():
            request["agent_wallet"] = self.auth.get_agent_wallet()
        else:
            request["agent_wallet"] = None  # Explicitly set to None for direct mode

        return request