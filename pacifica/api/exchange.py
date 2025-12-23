"""
Exchange API implementation - trading operations
"""

import uuid
import time
from typing import Dict, List, Optional, Any, Union
from .base import BaseAPIClient
import logging


logger = logging.getLogger(__name__)


class ExchangeAPI(BaseAPIClient):
    """Exchange API for trading operations (Hyperliquid-compatible)"""

    def _generate_client_order_id(self, cloid: Optional[str] = None) -> str:
        """
        Generate or validate client order ID.
        Pacifica requires standard UUID format, not Hyperliquid's 0x format.

        Args:
            cloid: Optional client order ID

        Returns:
            Valid UUID string
        """
        if cloid:
            if cloid.startswith("0x"):
                return str(uuid.uuid4())
            return cloid
        return str(uuid.uuid4())

    def order(
        self,
        name: str,
        is_buy: bool,
        sz: float,
        limit_px: float = None,
        order_type: Dict[str, Any] = {"limit": {"tif": "GTC"}},
        reduce_only: bool = False,
        cloid: Optional[str] = None,
        builder: Optional[Dict[str, Any]] = None
    ) -> Dict:
        """
        Place a single order (Hyperliquid-compatible).

        Args:
            name: Symbol to trade (Hyperliquid parameter)
            is_buy: True for buy, False for sell
            sz: Order size
            limit_px: Limit price
            order_type: Order type config (e.g., {"limit": {"tif": "GTC"}})
            reduce_only: Reduce only flag
            cloid: Client order ID
            builder: Optional builder dict {"b": "address", "f": fee_bps}

        Returns:
            Order response with status
        """
        client_order_id = self._generate_client_order_id(cloid)

        # Prepare order data
        order_data = {
            "symbol": name,
            "side": "bid" if is_buy else "ask",
            "amount": str(sz),
            "reduce_only": reduce_only,
            "client_order_id": client_order_id
            # TIF will be set based on order type
        }

        # Handle builder if provided
        if builder:
            if not isinstance(builder, dict) or "b" not in builder:
                raise ValueError("Builder must be dict with 'b' (address) and optional 'f' (fee)")
            # Map builder to Pacifica's format
            # NOTE: Pacifica only accepts builder address, fee is set at account level
            order_data["builder_code"] = builder["b"]
            # Pacifica ignores the 'f' field as fees are account-level, not per-order

        # Handle both string and dict formats for order_type
        if isinstance(order_type, str):
            if order_type.lower() == "limit":
                if limit_px is None:
                    raise ValueError("limit_px is required for limit orders")
                order_data["price"] = str(limit_px)
                # Default TIF for limit orders
                order_data["tif"] = "GTC"
                tif = "GTC"
            elif order_type.lower() == "market":
                # Market orders require slippage_percent instead of price
                order_data["slippage_percent"] = "0.5"  # Default 0.5% slippage
                # Remove price field if present
                if "price" in order_data:
                    del order_data["price"]
                # Market orders don't use TIF
                tif = None
        elif isinstance(order_type, dict):
            if "limit" in order_type:
                if limit_px is None:
                    raise ValueError("limit_px is required for limit orders")
                order_data["price"] = str(limit_px)
                tif = order_type["limit"].get("tif", "GTC")
                order_data["tif"] = tif  # Set initial TIF
            elif "market" in order_type:
                # Market orders require slippage_percent instead of price
                slippage = order_type.get("market", {}).get("slippage", "0.5")
                order_data["slippage_percent"] = str(slippage)
                # Remove price field if present
                if "price" in order_data:
                    del order_data["price"]
                # Market orders don't use TIF
                tif = None

        # Handle TIF settings - map Hyperliquid values to Pacifica format
        # Only apply TIF for limit orders (market orders don't have TIF)
        if tif:
            if tif == "Alo":
                order_data["post_only"] = True
                order_data["tif"] = "ALO"  # Pacifica uses ALO
            elif tif == "Ioc":
                order_data["tif"] = "IOC"
            elif tif == "Tob":
                order_data["tif"] = "TOB"
            # GTC is already set as default, but ensure it's uppercase
            elif tif in ["Gtc", "GTC"]:
                order_data["tif"] = "GTC"
        # For market orders, ensure no TIF is set
        elif "slippage_percent" in order_data and "tif" in order_data:
            del order_data["tif"]

        # Determine correct signature type based on order type
        if "slippage_percent" in order_data:
            signature_type = "create_market_order"
        else:
            signature_type = "create_limit_order"

        # Build authenticated request with agent wallet support
        request = self._build_request_with_auth(order_data, signature_type=signature_type)

        # Send request with operation type header (already includes auth, so authenticated=False)
        headers = {"type": signature_type}
        response = self.post("/orders/create", data=request, authenticated=False, headers=headers)

        # Extract order ID safely
        order_id = None
        if isinstance(response, dict):
            data = response.get("data", {})
            if isinstance(data, dict):
                order_id = data.get("order_id")

        return {
            "status": "ok",
            "response": {
                "type": "order",
                "data": {
                    "statuses": [{
                        "resting": {
                            "oid": order_id,
                            "cloid": client_order_id
                        }
                    }]
                }
            }
        }

    def batch_orders(self, orders: List[Dict]) -> Dict:
        """
        Place multiple orders in a single API call (Hyperliquid-compatible).

        Args:
            orders: List of order dictionaries with 'name' parameter

        Returns:
            Batch order response
        """
        # Transform orders to Pacifica batch format with actions
        actions = []

        for order_req in orders:
            client_order_id = self._generate_client_order_id(order_req.get("cloid"))

            # Create the order data that needs to be signed
            order_data = {
                "symbol": order_req.get("name") or order_req.get("coin"),  # Accept both 'name' (Hyperliquid) and 'coin' fields
                "side": "bid" if order_req["is_buy"] else "ask",
                "amount": str(order_req["sz"]),
                "reduce_only": order_req.get("reduce_only", False),
                "client_order_id": client_order_id
                # TIF will be set based on order type
            }

            # Handle builder dict if provided
            if "builder" in order_req:
                builder = order_req["builder"]
                if not isinstance(builder, dict) or "b" not in builder:
                    raise ValueError("Builder must be dict with 'b' (address) and optional 'f' (fee)")
                order_data["builder_code"] = builder["b"]
                if "f" in builder:
                    order_data["builder_fee"] = builder["f"]

            order_type = order_req.get("order_type", {"limit": {"tif": "GTC"}})

            # Handle both string and dict formats for order_type
            if isinstance(order_type, str):
                if order_type.lower() == "limit":
                    order_data["price"] = str(order_req["limit_px"])
                    order_data["tif"] = "GTC"  # Default TIF for limit orders
                    tif = "GTC"
                elif order_type.lower() == "market":
                    order_data["slippage_percent"] = "0.5"
                    # Market orders don't have TIF
                    tif = None
            elif isinstance(order_type, dict):
                if "limit" in order_type:
                    order_data["price"] = str(order_req["limit_px"])
                    tif = order_type["limit"].get("tif", "GTC")
                    order_data["tif"] = tif
                elif "market" in order_type:
                    order_data["slippage_percent"] = "0.5"
                    # Market orders don't have TIF
                    tif = None

            # Handle TIF settings for limit orders - Map Hyperliquid to Pacifica format
            if tif:
                if tif == "Alo":
                    order_data["post_only"] = True
                    order_data["tif"] = "ALO"
                elif tif == "Ioc":
                    order_data["tif"] = "IOC"
                elif tif == "Gtc" or tif == "GTC":
                    order_data["tif"] = "GTC"
                elif tif == "Tob":
                    order_data["tif"] = "TOB"

            # Determine correct signature type based on order type
            if "slippage_percent" in order_data:
                sig_type = "create_market_order"
            else:
                sig_type = "create_limit_order"

            # Build authenticated request for this order with agent wallet support
            signed_request = self._build_request_with_auth(order_data, signature_type=sig_type)

            # Add to actions list
            actions.append({
                "type": "Create",
                "data": signed_request
            })

        # Make single batch API call with actions
        batch_data = {"actions": actions}
        response = self.post("/orders/batch", data=batch_data, authenticated=False)  # Already signed

        # Transform response to Hyperliquid format
        statuses = []

        # Handle various response formats safely
        if isinstance(response, dict):
            results = response.get("data", {})
            if isinstance(results, dict):
                results = results.get("results", [])
            elif isinstance(results, list):
                # If data is already a list
                pass
            else:
                results = []
        else:
            # If response is not a dict, treat as error
            results = []

        for order_result in results:
            if isinstance(order_result, dict) and order_result.get("success"):
                statuses.append({
                    "resting": {
                        "oid": order_result.get("order_id"),
                        "cloid": order_result.get("client_order_id")
                    }
                })
            else:
                error_msg = "Unknown error"
                if isinstance(order_result, dict):
                    error_msg = order_result.get("error", error_msg)
                statuses.append({
                    "error": error_msg
                })

        return {
            "status": "ok",
            "response": {
                "type": "batchOrder",
                "data": {"statuses": statuses}
            }
        }

    def bulk_orders(self,
                   order_requests: List[Dict],
                   builder: Optional[Dict[str, Any]] = None,
                   grouping: str = 'na') -> Dict:
        """
        Place bulk orders (Hyperliquid-compatible).

        Args:
            order_requests: List of order dictionaries with 'name' parameter
            builder: Optional builder dict to apply to all orders
            grouping: Grouping type (default 'na')

        Returns:
            Batch order response in Hyperliquid format
        """
        # Add builder to each order if provided globally
        if builder:
            for order in order_requests:
                if 'builder' not in order:
                    order['builder'] = builder

        return self.batch_orders(order_requests)

    def cancel(self, name: str, oid: Optional[int] = None, cloid: Optional[str] = None) -> Dict:
        """
        Cancel an order (Hyperliquid-compatible).

        Args:
            name: Symbol to cancel (Hyperliquid parameter)
            oid: Order ID
            cloid: Client order ID

        Returns:
            Cancel response
        """
        # Prepare cancel data
        cancel_data = {"symbol": name}  # Map to Pacifica's 'symbol'

        if oid:
            cancel_data["order_id"] = oid
        elif cloid:
            cancel_data["client_order_id"] = cloid
        else:
            raise ValueError("Either oid or cloid must be provided")

        # Build authenticated request with agent wallet support
        request = self._build_request_with_auth(cancel_data, signature_type="cancel_order")

        # Send request (already includes auth, so authenticated=False)
        response = self.post("/orders/cancel", data=request, authenticated=False)

        return {
            "status": "ok",
            "response": {
                "type": "cancel",
                "data": {"statuses": ["success"]}
            }
        }

    def cancel_by_cloid(self, name: str, cloid: str) -> Dict:
        """
        Cancel order by client order ID (Hyperliquid-compatible).

        Args:
            name: Symbol (Hyperliquid parameter)
            cloid: Client order ID

        Returns:
            Cancel response
        """
        return self.cancel(name=name, cloid=cloid)

    def batch_cancel(self, cancels: List[Dict]) -> Dict:
        """
        Cancel multiple orders.
        Hyperliquid-compatible method.

        Note: Pacifica API doesn't have a batch cancel endpoint, so this
        implements batch cancellation as sequential individual cancels.

        Args:
            cancels: List of cancel requests with structure:
                [{"name": "BTC", "oid": 123}, {"name": "ETH", "cloid": "abc"}]

        Returns:
            Batch cancel response
        """
        statuses = []

        for cancel_req in cancels:
            try:
                # Use individual cancel method for each request
                symbol = cancel_req.get("name") or cancel_req.get("coin")
                if "oid" in cancel_req:
                    result = self.cancel(name=symbol, oid=cancel_req["oid"])
                elif "cloid" in cancel_req:
                    result = self.cancel(name=symbol, cloid=cancel_req["cloid"])
                else:
                    statuses.append("error")
                    continue

                # Check if cancel was successful
                if result.get("status") == "ok":
                    statuses.append("success")
                else:
                    statuses.append("error")

            except Exception as e:
                logger.error(f"Failed to cancel order {cancel_req}: {e}")
                statuses.append("error")

        return {
            "status": "ok",
            "response": {
                "type": "batchCancel",
                "data": {"statuses": statuses}
            }
        }

    def bulk_cancel(self, cancel_requests: List[Dict]) -> Dict:
        """
        Alias for batch_cancel (Hyperliquid compatibility).

        Args:
            cancel_requests: List of cancel requests

        Returns:
            Batch cancel response in Hyperliquid format
        """
        return self.batch_cancel(cancel_requests)

    def update_leverage(self, leverage: int, name: str, is_cross: bool = True) -> Dict:
        """
        Update leverage for a symbol (Hyperliquid-compatible).

        Args:
            leverage: Leverage value (1-100)
            name: Symbol (Hyperliquid parameter)
            is_cross: Use cross margin (True) or isolated (False)

        Returns:
            Update response
        """
        import time

        # Prepare request data with required signature fields
        timestamp = int(time.time() * 1000)
        data = {
            "account": self.auth.get_public_key() if self.auth else None,
            "symbol": name,
            "leverage": int(leverage),  # API expects integer, not string
            "timestamp": timestamp,
            "type": "update_leverage"
        }

        # Create signature for the request
        if self.auth:
            import json
            message_dict = {k: v for k, v in data.items() if k != 'signature'}
            message_str = json.dumps(message_dict, separators=(',', ':'), sort_keys=True)
            signature = self.auth.sign_request(message_str)
            data["signature"] = signature

        # Add operation type header
        headers = {"type": "update_leverage"}
        response = self.post("/account/leverage", data=data, headers=headers)

        return {
            "status": "ok" if response.get("success") else "err",
            "response": {
                "type": "updateLeverage",
                "data": response
            }
        }

    def update_margin_mode(self, name: str, is_cross: bool) -> Dict:
        """
        Update margin mode for a symbol (Hyperliquid-compatible).

        Args:
            name: Symbol (Hyperliquid parameter)
            is_cross: Use cross margin (True) or isolated (False)

        Returns:
            Update response
        """
        import time

        # Prepare request data with required signature fields
        timestamp = int(time.time() * 1000)
        data = {
            "account": self.auth.get_public_key() if self.auth else None,
            "symbol": name,
            "is_isolated": not is_cross,  # Pacifica uses is_isolated, opposite of is_cross
            "timestamp": timestamp,
            "type": "update_margin_mode"
        }

        # Create signature for the request
        if self.auth:
            import json
            message_dict = {k: v for k, v in data.items() if k != 'signature'}
            message_str = json.dumps(message_dict, separators=(',', ':'), sort_keys=True)
            signature = self.auth.sign_request(message_str)
            data["signature"] = signature

        # Add operation type header
        headers = {"type": "update_margin_mode"}
        response = self.post("/account/margin", data=data, headers=headers)

        return {
            "status": "ok" if response.get("success") else "err",
            "response": {
                "type": "updateMarginMode",
                "data": response
            }
        }

    def add_margin(self, name: str, amount: float) -> Dict:
        """
        Add margin to an isolated position (Hyperliquid-compatible).

        Args:
            name: Symbol (Hyperliquid parameter)
            amount: Margin amount to add

        Returns:
            Update response
        """
        import time

        # Prepare request data with required signature fields
        timestamp = int(time.time() * 1000)
        data = {
            "account": self.auth.get_public_key() if self.auth else None,
            "symbol": name,
            "amount": str(abs(amount)),  # Ensure positive for add
            "is_isolated": True,  # Margin adjustment only works for isolated positions
            "action": "add",
            "timestamp": timestamp,
            "type": "margin_action"
        }

        # Create signature for the request
        if self.auth:
            import json
            message_dict = {k: v for k, v in data.items() if k != 'signature'}
            message_str = json.dumps(message_dict, separators=(',', ':'), sort_keys=True)
            signature = self.auth.sign_request(message_str)
            data["signature"] = signature

        # Add operation type header
        headers = {"type": "margin_action"}
        response = self.post("/account/margin", data=data, headers=headers)

        return {
            "status": "ok" if response.get("success") else "err",
            "response": {
                "type": "addMargin",
                "data": response
            }
        }

    def remove_margin(self, name: str, amount: float) -> Dict:
        """
        Remove margin from an isolated position (Hyperliquid-compatible).

        Args:
            name: Symbol (Hyperliquid parameter)
            amount: Margin amount to remove

        Returns:
            Update response
        """
        import time

        # Prepare request data with required signature fields
        timestamp = int(time.time() * 1000)
        data = {
            "account": self.auth.get_public_key() if self.auth else None,
            "symbol": name,
            "amount": str(abs(amount)),  # Ensure positive for remove
            "is_isolated": True,  # Margin adjustment only works for isolated positions
            "action": "remove",
            "timestamp": timestamp,
            "type": "margin_action"
        }

        # Create signature for the request
        if self.auth:
            import json
            message_dict = {k: v for k, v in data.items() if k != 'signature'}
            message_str = json.dumps(message_dict, separators=(',', ':'), sort_keys=True)
            signature = self.auth.sign_request(message_str)
            data["signature"] = signature

        # Add operation type header
        headers = {"type": "margin_action"}
        response = self.post("/account/margin", data=data, headers=headers)

        return {
            "status": "ok" if response.get("success") else "err",
            "response": {
                "type": "removeMargin",
                "data": response
            }
        }

    def update_isolated_margin(self, amount: float, name: str) -> Dict:
        """
        Update isolated margin (Hyperliquid-specific method).

        Args:
            amount: Amount to add (positive) or remove (negative)
            name: Symbol (Hyperliquid parameter)

        Returns:
            Update response
        """
        if amount > 0:
            return self.add_margin(name=name, amount=amount)
        else:
            return self.remove_margin(name=name, amount=abs(amount))

    def market_open(
        self,
        name: str,
        is_buy: bool,
        sz: float,
        px: Optional[float] = None,
        slippage: float = 0.05,
        cloid: Optional[str] = None,
        builder: Optional[Dict[str, Any]] = None
    ) -> Dict:
        """
        Open market position (Hyperliquid-compatible).

        Args:
            name: Symbol to trade
            is_buy: Direction (True for buy, False for sell)
            sz: Size
            px: Optional limit price
            slippage: Slippage tolerance (default 5%)
            cloid: Client order ID
            builder: Optional builder dict {"b": "address", "f": fee_bps}

        Returns:
            Order response
        """
        # If px provided, it's a limit order with IOC
        if px:
            order_type = {"limit": {"tif": "Ioc"}}
            limit_price = px
        else:
            order_type = {"market": {}}
            # For market orders, we might need to provide a limit price with slippage
            # This would depend on Pacifica's API requirements
            limit_price = 0  # Or calculate based on current price + slippage

        return self.order(
            name=name,
            is_buy=is_buy,
            sz=sz,
            limit_px=limit_price,
            order_type=order_type,
            reduce_only=False,
            cloid=cloid,
            builder=builder
        )

    def market_close(
        self,
        coin: str,  # NOTE: Hyperliquid uses 'coin' here, not 'name'!
        sz: Optional[float] = None,
        px: Optional[float] = None,
        slippage: float = 0.05,
        cloid: Optional[str] = None,
        builder: Optional[Dict[str, Any]] = None
    ) -> Dict:
        """
        Close market position (Hyperliquid-compatible).

        IMPORTANT: Hyperliquid uses 'coin' parameter here, not 'name'!

        Args:
            coin: Symbol to close (NOTE: uses 'coin' not 'name')
            sz: Size to close (None = close entire position)
            px: Optional limit price
            slippage: Slippage tolerance (default 5%)
            cloid: Client order ID
            builder: Optional builder dict

        Returns:
            Order response
        """
        # TODO: Need to determine position direction to know if we should buy or sell
        # For now, this is a placeholder implementation
        # In practice, you'd need to fetch the current position to determine direction

        # If px provided, it's a limit order with IOC
        if px:
            order_type = {"limit": {"tif": "Ioc"}}
            limit_price = px
        else:
            order_type = {"market": {}}
            limit_price = 0

        # Map 'coin' to 'name' for internal call
        return self.order(
            name=coin,  # Map 'coin' parameter to 'name'
            is_buy=False,  # This needs to be determined from position
            sz=sz or 0,  # If sz is None, need to get position size
            limit_px=limit_price,
            order_type=order_type,
            reduce_only=True,
            cloid=cloid,
            builder=builder
        )