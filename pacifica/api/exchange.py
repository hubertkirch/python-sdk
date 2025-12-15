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
        coin: str,
        is_buy: bool,
        sz: float,
        limit_px: float,
        order_type: Dict[str, Any],
        reduce_only: bool = False,
        cloid: Optional[str] = None
    ) -> Dict:
        """
        Place a single order.
        Hyperliquid-compatible method.

        Args:
            coin: Symbol/coin name
            is_buy: True for buy, False for sell
            sz: Order size
            limit_px: Limit price
            order_type: Order type config (e.g., {"limit": {"tif": "Gtc"}})
            reduce_only: Reduce only flag
            cloid: Client order ID

        Returns:
            Order response with status
        """
        client_order_id = self._generate_client_order_id(cloid)

        # Prepare order data
        order_data = {
            "symbol": coin,
            "side": "bid" if is_buy else "ask",
            "amount": str(sz),
            "reduce_only": reduce_only,
            "client_order_id": client_order_id,
            "tif": "GTC"  # Default time in force
        }

        if "limit" in order_type:
            order_data["price"] = str(limit_px)
            tif = order_type["limit"].get("tif", "Gtc")
            if tif == "Alo":
                order_data["post_only"] = True
            elif tif == "Ioc":
                order_data["tif"] = "IOC"
            elif tif == "Tob":
                order_data["tif"] = "TOB"
        elif "market" in order_type:
            order_data["type"] = "market"

        # Build authenticated request with agent wallet support
        request = self._build_request_with_auth(order_data, signature_type="create_order")

        # Send request (already includes auth, so authenticated=False)
        response = self.post("/api/v1/orders/create", data=request, authenticated=False)

        return {
            "status": "ok",
            "response": {
                "type": "order",
                "data": {
                    "statuses": [{
                        "resting": {
                            "oid": response.get("data", {}).get("order_id"),
                            "cloid": client_order_id
                        }
                    }]
                }
            }
        }

    def batch_orders(self, orders: List[Dict]) -> Dict:
        """
        Place multiple orders in a single API call.
        Hyperliquid-compatible method.

        Args:
            orders: List of order dictionaries

        Returns:
            Batch order response
        """
        # Transform orders to Pacifica batch format with actions
        actions = []

        for order_req in orders:
            client_order_id = self._generate_client_order_id(order_req.get("cloid"))

            # Create the order data that needs to be signed
            order_data = {
                "symbol": order_req["coin"],
                "side": "bid" if order_req["is_buy"] else "ask",
                "amount": str(order_req["sz"]),
                "reduce_only": order_req.get("reduce_only", False),
                "client_order_id": client_order_id,
                "tif": "GTC"  # Default time in force
            }

            order_type = order_req.get("order_type", {"limit": {"tif": "Gtc"}})

            if "limit" in order_type:
                order_data["price"] = str(order_req["limit_px"])
                tif = order_type["limit"].get("tif", "Gtc")
                if tif == "Alo":
                    order_data["post_only"] = True
                elif tif == "Ioc":
                    order_data["tif"] = "IOC"
            elif "market" in order_type:
                order_data["slippage_percent"] = "0.5"

            # Build authenticated request for this order with agent wallet support
            signed_request = self._build_request_with_auth(order_data, signature_type="create_order")

            # Add to actions list
            actions.append({
                "type": "Create",
                "data": signed_request
            })

        # Make single batch API call with actions
        batch_data = {"actions": actions}
        response = self.post("/api/v1/orders/batch", data=batch_data, authenticated=False)  # Already signed

        # Transform response to Hyperliquid format
        statuses = []
        for order_result in response.get("data", {}).get("results", []):
            if order_result.get("success"):
                statuses.append({
                    "resting": {
                        "oid": order_result.get("order_id"),
                        "cloid": order_result.get("client_order_id")
                    }
                })
            else:
                statuses.append({
                    "error": order_result.get("error", "Unknown error")
                })

        return {
            "status": "ok",
            "response": {
                "type": "batchOrder",
                "data": {"statuses": statuses}
            }
        }

    def bulk_orders(self, order_requests: List[Dict]) -> Dict:
        """
        Place multiple orders atomically - Hyperliquid-compatible alias.

        This is the Hyperliquid-compatible method name for batch_orders.

        Args:
            order_requests: List of order dictionaries with keys:
                - coin, is_buy, sz, limit_px, order_type, reduce_only, cloid

        Returns:
            Batch order response in Hyperliquid format
        """
        return self.batch_orders(order_requests)

    def cancel(self, coin: str, oid: Optional[int] = None, cloid: Optional[str] = None) -> Dict:
        """
        Cancel an order.
        Hyperliquid-compatible method.

        Args:
            coin: Symbol/coin name
            oid: Order ID
            cloid: Client order ID

        Returns:
            Cancel response
        """
        # Prepare cancel data
        cancel_data = {"symbol": coin}

        if oid:
            cancel_data["order_id"] = oid
        elif cloid:
            cancel_data["client_order_id"] = cloid
        else:
            raise ValueError("Either oid or cloid must be provided")

        # Build authenticated request with agent wallet support
        request = self._build_request_with_auth(cancel_data, signature_type="cancel_order")

        # Send request (already includes auth, so authenticated=False)
        response = self.post("/api/v1/orders/cancel", data=request, authenticated=False)

        return {
            "status": "ok",
            "response": {
                "type": "cancel",
                "data": {"statuses": ["success"]}
            }
        }

    def cancel_by_cloid(self, coin: str, cloid: str) -> Dict:
        """
        Cancel order by client order ID.
        Hyperliquid-compatible method.

        Args:
            coin: Symbol/coin name
            cloid: Client order ID

        Returns:
            Cancel response
        """
        return self.cancel(coin=coin, cloid=cloid)

    def batch_cancel(self, cancels: List[Dict]) -> Dict:
        """
        Cancel multiple orders.
        Hyperliquid-compatible method.

        Note: Pacifica API doesn't have a batch cancel endpoint, so this
        implements batch cancellation as sequential individual cancels.

        Args:
            cancels: List of cancel requests with structure:
                [{"coin": "BTC", "oid": 123}, {"coin": "ETH", "cloid": "abc"}]

        Returns:
            Batch cancel response
        """
        statuses = []

        for cancel_req in cancels:
            try:
                # Use individual cancel method for each request
                if "oid" in cancel_req:
                    result = self.cancel(coin=cancel_req["coin"], oid=cancel_req["oid"])
                elif "cloid" in cancel_req:
                    result = self.cancel(coin=cancel_req["coin"], cloid=cancel_req["cloid"])
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

    def update_leverage(self, coin: str, leverage: int, is_cross: bool = True) -> Dict:
        """
        Update leverage for a symbol.
        Hyperliquid-compatible method.

        Args:
            coin: Symbol/coin name
            leverage: Leverage value (1-100)
            is_cross: Use cross margin (True) or isolated (False)

        Returns:
            Update response
        """
        import time

        # Prepare request data with required signature fields
        timestamp = int(time.time() * 1000)
        data = {
            "account": self.auth.get_public_key() if self.auth else None,
            "symbol": coin,
            "leverage": leverage,
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
        response = self.post("/api/v1/account/leverage", data=data, headers=headers)

        return {
            "status": "ok" if response.get("success") else "err",
            "response": {
                "type": "updateLeverage",
                "data": response
            }
        }

    def update_margin_mode(self, coin: str, is_cross: bool) -> Dict:
        """
        Update margin mode for a symbol.
        Hyperliquid-compatible method.

        Args:
            coin: Symbol/coin name
            is_cross: Use cross margin (True) or isolated (False)

        Returns:
            Update response
        """
        import time

        # Prepare request data with required signature fields
        timestamp = int(time.time() * 1000)
        data = {
            "account": self.auth.get_public_key() if self.auth else None,
            "symbol": coin,
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
        response = self.post("/api/v1/account/margin", data=data, headers=headers)

        return {
            "status": "ok" if response.get("success") else "err",
            "response": {
                "type": "updateMarginMode",
                "data": response
            }
        }

    def add_margin(self, coin: str, amount: float) -> Dict:
        """
        Add margin to an isolated position.
        Hyperliquid-compatible method.

        Args:
            coin: Symbol/coin name
            amount: Margin amount to add

        Returns:
            Update response
        """
        import time

        # Prepare request data with required signature fields
        timestamp = int(time.time() * 1000)
        data = {
            "account": self.auth.get_public_key() if self.auth else None,
            "symbol": coin,
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
        response = self.post("/api/v1/account/margin", data=data, headers=headers)

        return {
            "status": "ok" if response.get("success") else "err",
            "response": {
                "type": "addMargin",
                "data": response
            }
        }

    def remove_margin(self, coin: str, amount: float) -> Dict:
        """
        Remove margin from an isolated position.
        Hyperliquid-compatible method.

        Args:
            coin: Symbol/coin name
            amount: Margin amount to remove

        Returns:
            Update response
        """
        import time

        # Prepare request data with required signature fields
        timestamp = int(time.time() * 1000)
        data = {
            "account": self.auth.get_public_key() if self.auth else None,
            "symbol": coin,
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
        response = self.post("/api/v1/account/margin", data=data, headers=headers)

        return {
            "status": "ok" if response.get("success") else "err",
            "response": {
                "type": "removeMargin",
                "data": response
            }
        }