"""
Info API implementation - read-only data methods
"""

from typing import Dict, List, Optional, Any
from .base import BaseAPIClient
from ..transformers.account import AccountTransformer
from ..transformers.market import MarketTransformer
from ..exceptions import PacificaAccountNotFoundError
import logging


logger = logging.getLogger(__name__)


class InfoAPI(BaseAPIClient):
    """Info API for read-only data access (Hyperliquid-compatible)"""

    def _get_position_leverage(self, symbol: str, account: Optional[str] = None) -> Optional[int]:
        """
        Get the actual leverage for a position.

        Logic:
        1. Check account settings for custom leverage
        2. If not found, use max leverage from market info

        Args:
            symbol: Symbol to get leverage for
            account: Account address

        Returns:
            Leverage value or None if not found
        """
        if not account and self.auth:
            account = self.auth.get_account()  # Use get_account() for agent mode support

        # Step 1: Check account settings for custom leverage
        try:
            settings_response = self.get(
                "/api/v1/account/settings",
                params={"account": account}
            )

            data = settings_response.get('data', {})

            # Handle different response formats
            if isinstance(data, dict) and symbol in data:
                if isinstance(data[symbol], dict) and 'leverage' in data[symbol]:
                    return data[symbol]['leverage']

            elif isinstance(data, list) and len(data) > 0:
                for item in data:
                    if isinstance(item, dict) and item.get('symbol') == symbol:
                        if 'leverage' in item:
                            return item['leverage']
        except Exception as e:
            logger.debug(f"Failed to get account settings: {e}")

        # Step 2: Get max leverage from market info
        try:
            info_response = self.get("/api/v1/info")
            markets = info_response.get('data', [])

            if isinstance(markets, list):
                for market in markets:
                    if market.get('symbol') == symbol:
                        max_lev = market.get('max_leverage') or market.get('maxLeverage')
                        if max_lev:
                            return max_lev
        except Exception as e:
            logger.debug(f"Failed to get market info: {e}")

        return None

    def user_state(self, address: Optional[str] = None) -> Dict:
        """
        Get user state (account + positions).
        Hyperliquid-compatible method.
        Now includes leverage discovery with optimized fetching!

        Args:
            address: User address (optional, uses auth address if not provided)

        Returns:
            User state in Hyperliquid format
        """
        if not address and self.auth:
            address = self.auth.get_account()  # Use get_account() for agent mode support

        # Fetch account data
        try:
            account_response = self.get(
                "/api/v1/account",
                params={"account": address}
            )
        except PacificaAccountNotFoundError:
            account_response = {"data": {
                "balance": "0",
                "account_equity": "0",
                "total_margin_used": "0",
                "cross_mmr": "0",
                "available_to_withdraw": "0"
            }}

        # Fetch positions
        positions_response = self.get(
            "/api/v1/positions",
            params={"account": address}
        )

        positions = positions_response.get('data', [])

        # Only fetch settings and market info if we have positions
        if positions:
            # Fetch account settings and market info ONCE for all positions
            try:
                settings_response = self.get(
                    "/api/v1/account/settings",
                    params={"account": address}
                )
                settings_data = settings_response.get('data', {})
            except:
                settings_data = {}

            try:
                info_response = self.get("/api/v1/info")
                markets_data = info_response.get('data', [])
            except:
                markets_data = []

            # Build a map of max leverages for quick lookup
            max_leverage_map = {}
            if isinstance(markets_data, list):
                for market in markets_data:
                    symbol = market.get('symbol')
                    max_lev = market.get('max_leverage') or market.get('maxLeverage')
                    if symbol and max_lev:
                        max_leverage_map[symbol] = max_lev

            # Add leverage to each position using the fetched data
            for position in positions:
                symbol = position.get('symbol')
                if symbol:
                    leverage = None

                    # Check account settings first
                    if isinstance(settings_data, dict) and symbol in settings_data:
                        if isinstance(settings_data[symbol], dict) and 'leverage' in settings_data[symbol]:
                            leverage = settings_data[symbol]['leverage']
                    elif isinstance(settings_data, list):
                        for item in settings_data:
                            if isinstance(item, dict) and item.get('symbol') == symbol:
                                if 'leverage' in item:
                                    leverage = item['leverage']
                                    break

                    # Fall back to max leverage if no custom setting
                    if leverage is None:
                        leverage = max_leverage_map.get(symbol)

                    if leverage:
                        position['leverage'] = leverage

        return AccountTransformer.transform_user_state(
            account_response,
            positions_response
        )

    def open_orders(self, address: Optional[str] = None) -> List[Dict]:
        """
        Get open orders.
        Hyperliquid-compatible method.

        Args:
            address: User address (optional, uses auth address if not provided)

        Returns:
            Open orders in Hyperliquid format
        """
        if not address and self.auth:
            address = self.auth.get_account()  # Use get_account() for agent mode support

        response = self.get(
            "/api/v1/orders",
            params={"account": address}
        )

        return AccountTransformer.transform_open_orders(response)

    def user_fills(self, address: Optional[str] = None, oid: Optional[int] = None) -> List[Dict]:
        """
        Get user fills (trade history).
        Hyperliquid-compatible method.

        Args:
            address: User address (optional, uses auth address if not provided)
            oid: Optional order ID to filter fills

        Returns:
            User fills in Hyperliquid format
        """
        if not address and self.auth:
            address = self.auth.get_account()  # Use get_account() for agent mode support

        response = self.get(
            "/api/v1/trades/history",
            params={"account": address}
        )

        return AccountTransformer.transform_user_fills(response, oid)

    def user_funding(self, address: Optional[str] = None, start_time: int = 0) -> List[Dict]:
        """
        Get user funding history.
        Hyperliquid-compatible method.

        Args:
            address: User address (optional, uses auth address if not provided)
            start_time: Start timestamp (milliseconds)

        Returns:
            Funding history in Hyperliquid format
        """
        if not address and self.auth:
            address = self.auth.get_account()  # Use get_account() for agent mode support

        params = {"account": address}
        if start_time > 0:
            params["start_time"] = start_time

        try:
            response = self.get("/api/v1/funding/history", params=params)
        except:
            response = {"data": []}

        return AccountTransformer.transform_funding_history(response)

    def meta(self) -> Dict:
        """
        Get market metadata.
        Hyperliquid-compatible method.

        Returns:
            Market metadata in Hyperliquid format
        """
        response = self.get("/api/v1/info")
        return MarketTransformer.transform_meta(response)

    def all_mids(self) -> Dict:
        """
        Get all mid prices.
        Hyperliquid-compatible method.

        Returns:
            Mid prices for all markets in Hyperliquid format
        """
        response = self.get("/api/v1/info/prices")
        return MarketTransformer.transform_all_mids(response)

    def l2_book(self, coin: str) -> Dict:
        """
        Get L2 orderbook.
        Hyperliquid-compatible method.

        Args:
            coin: Symbol/coin name

        Returns:
            L2 orderbook in Hyperliquid format
        """
        response = self.get(
            "/api/v1/book",
            params={"symbol": coin}
        )
        return MarketTransformer.transform_l2_book(response)

    def candles(self, coin: str, interval: str, start_time: int, end_time: int) -> List[Dict]:
        """
        Get candlestick data.
        Hyperliquid-compatible method.

        Args:
            coin: Symbol/coin name
            interval: Time interval (1m, 5m, 15m, 1h, 4h, 1d)
            start_time: Start timestamp (milliseconds)
            end_time: End timestamp (milliseconds)

        Returns:
            Candles in Hyperliquid format
        """
        response = self.get(
            "/api/v1/candles",
            params={
                "symbol": coin,
                "interval": interval,
                "start_time": start_time,
                "end_time": end_time
            }
        )
        return MarketTransformer.transform_candles(response, coin, interval)

    def funding_rates(self) -> List[Dict]:
        """
        Get current funding rates.
        Hyperliquid-compatible method.

        Returns:
            Funding rates in Hyperliquid format
        """
        try:
            response = self.get("/api/v1/funding/rates")
        except:
            response = {"data": []}

        return MarketTransformer.transform_funding_rates(response)

    def open_interest(self) -> Dict:
        """
        Get open interest for all markets.
        Hyperliquid-compatible method.

        Returns:
            Open interest in Hyperliquid format
        """
        try:
            response = self.get("/api/v1/stats/open_interest")
        except:
            response = {"data": []}

        return MarketTransformer.transform_open_interest(response)

    def get_position_leverage(self, symbol: str, address: Optional[str] = None) -> Optional[int]:
        """
        Public method to get position leverage.

        Args:
            symbol: Symbol to get leverage for
            address: Account address (optional)

        Returns:
            Leverage value or None if not found
        """
        return self._get_position_leverage(symbol, address)