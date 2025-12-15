"""
Async Pacifica client for high-performance parallel API calls
"""

import asyncio
import aiohttp
import json
import time
from typing import Dict, List, Optional, Any
from .auth import PacificaAuth
from .transformers.account import AccountTransformer
from .transformers.market import MarketTransformer
from .exceptions import PacificaAPIError, PacificaAccountNotFoundError


class AsyncPacificaClient:
    """
    Async client for Pacifica with parallel API calls.
    Provides massive speed improvements for multi-endpoint operations.
    """

    MAINNET_API = "https://api.pacifica.fi"
    TESTNET_API = "https://test-api.pacifica.fi"

    def __init__(
        self,
        private_key: Optional[str] = None,
        base_url: Optional[str] = None,
        testnet: bool = False,
        timeout: int = 30
    ):
        """Initialize async client"""
        self.auth = PacificaAuth(private_key) if private_key else None
        self.timeout = aiohttp.ClientTimeout(total=timeout)

        if base_url:
            self.base_url = base_url
        elif testnet:
            self.base_url = self.TESTNET_API
        else:
            self.base_url = self.MAINNET_API

        self.session = None

    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=self.timeout,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        headers: Optional[Dict] = None
    ) -> Dict:
        """Make async API request"""
        if not self.session:
            raise RuntimeError("Client not initialized. Use 'async with AsyncPacificaClient() as client:'")

        url = f"{self.base_url}{endpoint}"

        # Add account to params if auth is available
        if self.auth and params is None:
            params = {}
        if self.auth and params is not None and "account" not in params:
            params["account"] = self.auth.get_public_key()

        # Prepare request headers
        req_headers = {}
        if headers:
            req_headers.update(headers)

        try:
            async with self.session.request(
                method,
                url,
                params=params,
                json=data,
                headers=req_headers
            ) as response:
                result = await response.json()

                if response.status == 404 and "account" in str(url):
                    raise PacificaAccountNotFoundError(params.get("account", "unknown"))

                if response.status >= 400:
                    raise PacificaAPIError(
                        response.status,
                        result.get("msg", result.get("error", "Unknown error"))
                    )

                return result

        except asyncio.TimeoutError:
            raise PacificaAPIError(408, "Request timeout")

    async def user_state(self, address: Optional[str] = None) -> Dict:
        """
        Get user state with parallel fetching.
        This is the optimized version that fetches everything in parallel.
        """
        if not address and self.auth:
            address = self.auth.get_public_key()

        # First, fetch account and positions in parallel
        tasks = [
            self._request("GET", "/api/v1/account", params={"account": address}),
            self._request("GET", "/api/v1/positions", params={"account": address})
        ]

        try:
            account_response, positions_response = await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            account_response = {"data": {
                "balance": "0",
                "account_equity": "0",
                "total_margin_used": "0",
                "cross_mmr": "0",
                "available_to_withdraw": "0"
            }}
            positions_response = {"data": []}

        # Handle exceptions
        if isinstance(account_response, Exception):
            account_response = {"data": {
                "balance": "0",
                "account_equity": "0",
                "total_margin_used": "0",
                "cross_mmr": "0",
                "available_to_withdraw": "0"
            }}

        if isinstance(positions_response, Exception):
            positions_response = {"data": []}

        positions = positions_response.get('data', [])

        # If we have positions, fetch leverage data in parallel
        if positions:
            leverage_tasks = [
                self._request("GET", "/api/v1/account/settings", params={"account": address}),
                self._request("GET", "/api/v1/info")
            ]

            try:
                settings_response, info_response = await asyncio.gather(*leverage_tasks, return_exceptions=True)
            except:
                settings_response = {"data": {}}
                info_response = {"data": []}

            # Handle exceptions
            if isinstance(settings_response, Exception):
                settings_response = {"data": {}}
            if isinstance(info_response, Exception):
                info_response = {"data": []}

            settings_data = settings_response.get('data', {})
            markets_data = info_response.get('data', [])

            # Build leverage map
            max_leverage_map = {}
            if isinstance(markets_data, list):
                for market in markets_data:
                    symbol = market.get('symbol')
                    max_lev = market.get('max_leverage') or market.get('maxLeverage')
                    if symbol and max_lev:
                        max_leverage_map[symbol] = max_lev

            # Add leverage to positions
            for position in positions:
                symbol = position.get('symbol')
                if symbol:
                    leverage = None

                    # Check custom settings
                    if isinstance(settings_data, dict) and symbol in settings_data:
                        if isinstance(settings_data[symbol], dict) and 'leverage' in settings_data[symbol]:
                            leverage = settings_data[symbol]['leverage']
                    elif isinstance(settings_data, list):
                        for item in settings_data:
                            if isinstance(item, dict) and item.get('symbol') == symbol:
                                if 'leverage' in item:
                                    leverage = item['leverage']
                                    break

                    # Fall back to max leverage
                    if leverage is None:
                        leverage = max_leverage_map.get(symbol)

                    if leverage:
                        position['leverage'] = leverage

        return AccountTransformer.transform_user_state(
            account_response,
            positions_response
        )

    async def batch_fetch(self, endpoints: Dict[str, tuple]) -> Dict[str, Any]:
        """
        Fetch multiple endpoints in parallel.

        Args:
            endpoints: Dict of {name: (method, endpoint, params)}

        Returns:
            Dict of {name: response}

        Example:
            results = await client.batch_fetch({
                'account': ('GET', '/api/v1/account', {'account': address}),
                'positions': ('GET', '/api/v1/positions', {'account': address}),
                'orders': ('GET', '/api/v1/orders', {'account': address})
            })
        """
        tasks = []
        names = []

        for name, (method, endpoint, params) in endpoints.items():
            tasks.append(self._request(method, endpoint, params=params))
            names.append(name)

        results = {}
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        for name, response in zip(names, responses):
            if isinstance(response, Exception):
                results[name] = {"error": str(response)}
            else:
                results[name] = response

        return results

    # Synchronous wrapper methods for compatibility

    def user_state_sync(self, address: Optional[str] = None) -> Dict:
        """Synchronous wrapper for user_state"""
        return asyncio.run(self.user_state(address))

    @classmethod
    async def create(cls, private_key: Optional[str] = None, **kwargs):
        """Factory method to create and initialize client"""
        client = cls(private_key, **kwargs)
        client.session = aiohttp.ClientSession(
            timeout=client.timeout,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
        )
        return client


# Example usage function
async def example_parallel_fetch():
    """Example of parallel fetching"""
    async with AsyncPacificaClient(private_key="your_key") as client:
        # Fetch multiple data points in parallel
        account_data, positions, orders = await asyncio.gather(
            client.user_state(),
            client._request("GET", "/api/v1/positions"),
            client._request("GET", "/api/v1/orders")
        )

        print(f"Account value: {account_data['marginSummary']['accountValue']}")
        print(f"Positions: {len(positions.get('data', []))}")
        print(f"Open orders: {len(orders.get('data', []))}")

        # Or use batch_fetch for named results
        results = await client.batch_fetch({
            'prices': ('GET', '/api/v1/info/prices', {}),
            'markets': ('GET', '/api/v1/info', {}),
            'book_btc': ('GET', '/api/v1/book', {'symbol': 'BTC'})
        })

        print(f"BTC orderbook: {results['book_btc']}")