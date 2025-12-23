"""
Async Exchange API implementation with parallel execution optimization
"""

import asyncio
import uuid
import time
from typing import Dict, List, Optional, Any, Union
from .base_async import BaseAsyncAPIClient
import logging


logger = logging.getLogger(__name__)


class ExchangeAsyncAPI(BaseAsyncAPIClient):
    """Async Exchange API with optimized parallel execution for batch operations"""

    def _generate_client_order_id(self, cloid: Optional[str] = None) -> str:
        """Generate or validate client order ID."""
        if cloid:
            if cloid.startswith("0x"):
                return str(uuid.uuid4())
            return cloid
        return str(uuid.uuid4())

    async def order(
        self,
        name: str,
        is_buy: bool,
        sz: float,
        limit_px: float,
        order_type: Dict[str, Any],
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
            order_type: Order type config
            reduce_only: Reduce only flag
            cloid: Client order ID
            builder: Optional builder dict {"b": "address", "f": fee_bps}

        Returns:
            Order response with status
        """
        client_order_id = self._generate_client_order_id(cloid)

        order_data = {
            "symbol": name,
            "side": "bid" if is_buy else "ask",
            "amount": str(sz),
            "reduce_only": reduce_only,
            "client_order_id": client_order_id,
            "tif": "GTC"
        }

        # Handle builder if provided
        if builder:
            if not isinstance(builder, dict) or "b" not in builder:
                raise ValueError("Builder must be dict with 'b' (address) and optional 'f' (fee)")
            order_data["builder_code"] = builder["b"]
            if "f" in builder:
                order_data["builder_fee"] = builder["f"]

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

        request = self._build_request_with_auth(order_data, signature_type="create_order")
        response = await self.post("/orders/create", data=request, authenticated=False)

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

    async def batch_orders(self, orders: List[Dict]) -> Dict:
        """
        Place multiple orders in a single API call (Hyperliquid-compatible).

        Args:
            orders: List of order dictionaries with 'name' parameter

        Returns:
            Batch order response
        """
        actions = []

        for order_req in orders:
            client_order_id = self._generate_client_order_id(order_req.get("cloid"))

            order_data = {
                "symbol": order_req.get("name") or order_req.get("coin"),  # Accept both 'name' (Hyperliquid) and 'coin' fields
                "side": "bid" if order_req["is_buy"] else "ask",
                "amount": str(order_req["sz"]),
                "reduce_only": order_req.get("reduce_only", False),
                "client_order_id": client_order_id,
                "tif": "GTC"
            }

            # Handle builder dict if provided
            if "builder" in order_req:
                builder = order_req["builder"]
                if not isinstance(builder, dict) or "b" not in builder:
                    raise ValueError("Builder must be dict with 'b' (address) and optional 'f' (fee)")
                order_data["builder_code"] = builder["b"]
                if "f" in builder:
                    order_data["builder_fee"] = builder["f"]

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

            signed_request = self._build_request_with_auth(order_data, signature_type="create_order")

            actions.append({
                "type": "Create",
                "data": signed_request
            })

        batch_data = {"actions": actions}
        response = await self.post("/orders/batch", data=batch_data, authenticated=False)

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

    async def bulk_orders(self,
                        order_requests: List[Dict],
                        builder: Optional[Dict[str, Any]] = None,
                        grouping: str = 'na') -> Dict:
        """Place bulk orders (Hyperliquid-compatible).

        Args:
            order_requests: List of order dictionaries with 'name' parameter
            builder: Optional builder dict to apply to all orders
            grouping: Grouping type (default 'na')
        """
        # Add builder to each order if provided globally
        if builder:
            for order in order_requests:
                if 'builder' not in order:
                    order['builder'] = builder

        return await self.batch_orders(order_requests)

    async def cancel(self, name: str, oid: Optional[int] = None, cloid: Optional[str] = None) -> Dict:
        """
        Cancel an order (Hyperliquid-compatible).

        Args:
            name: Symbol (Hyperliquid parameter)
            oid: Order ID
            cloid: Client order ID

        Returns:
            Cancel response
        """
        cancel_data = {"symbol": name}

        if oid:
            cancel_data["order_id"] = oid
        elif cloid:
            cancel_data["client_order_id"] = cloid
        else:
            raise ValueError("Either oid or cloid must be provided")

        request = self._build_request_with_auth(cancel_data, signature_type="cancel_order")
        response = await self.post("/orders/cancel", data=request, authenticated=False)

        return {
            "status": "ok",
            "response": {
                "type": "cancel",
                "data": {"statuses": ["success"]}
            }
        }

    async def cancel_by_cloid(self, name: str, cloid: str) -> Dict:
        """Cancel order by client order ID (Hyperliquid-compatible)."""
        return await self.cancel(name=name, cloid=cloid)

    async def batch_cancel(self, cancels: List[Dict]) -> Dict:
        """
        Cancel multiple orders IN PARALLEL.
        Optimized from N sequential calls to parallel execution.

        Args:
            cancels: List of cancel requests

        Returns:
            Batch cancel response with all cancellations executed in parallel
        """
        # Create cancel tasks for all orders
        cancel_tasks = []

        for cancel_req in cancels:
            if "oid" in cancel_req:
                task = self.cancel(name=cancel_req["name"], oid=cancel_req["oid"])
            elif "cloid" in cancel_req:
                task = self.cancel(name=cancel_req["name"], cloid=cancel_req["cloid"])
            else:
                # Create a completed task with error status for invalid requests
                async def error_task():
                    return {"status": "error"}
                task = error_task()

            cancel_tasks.append(task)

        # Execute all cancels in parallel - this is the key optimization
        results = await asyncio.gather(*cancel_tasks, return_exceptions=True)

        # Process results
        statuses = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Failed to cancel order {cancels[i]}: {result}")
                statuses.append("error")
            elif isinstance(result, dict) and result.get("status") == "ok":
                statuses.append("success")
            else:
                statuses.append("error")

        return {
            "status": "ok",
            "response": {
                "type": "batchCancel",
                "data": {"statuses": statuses}
            }
        }

    async def bulk_cancel(self, cancel_requests: List[Dict]) -> Dict:
        """Alias for batch_cancel (Hyperliquid compatibility)."""
        return await self.batch_cancel(cancel_requests)

    async def update_leverage(self, leverage: int, name: str, is_cross: bool = True) -> Dict:
        """Update leverage for a symbol (Hyperliquid-compatible)."""
        timestamp = int(time.time() * 1000)
        data = {
            "account": self.auth.get_public_key() if self.auth else None,
            "symbol": name,
            "leverage": leverage,
            "timestamp": timestamp,
            "type": "update_leverage"
        }

        if self.auth:
            import json
            message_dict = {k: v for k, v in data.items() if k != 'signature'}
            message_str = json.dumps(message_dict, separators=(',', ':'), sort_keys=True)
            signature = self.auth.sign_request(message_str)
            data["signature"] = signature

        headers = {"type": "update_leverage"}
        response = await self.post("/account/leverage", data=data, headers=headers)

        return {
            "status": "ok" if response.get("success") else "err",
            "response": {
                "type": "updateLeverage",
                "data": response
            }
        }

    async def update_margin_mode(self, name: str, is_cross: bool) -> Dict:
        """Update margin mode for a symbol (Hyperliquid-compatible)."""
        timestamp = int(time.time() * 1000)
        data = {
            "account": self.auth.get_public_key() if self.auth else None,
            "symbol": name,
            "is_isolated": not is_cross,
            "timestamp": timestamp,
            "type": "update_margin_mode"
        }

        if self.auth:
            import json
            message_dict = {k: v for k, v in data.items() if k != 'signature'}
            message_str = json.dumps(message_dict, separators=(',', ':'), sort_keys=True)
            signature = self.auth.sign_request(message_str)
            data["signature"] = signature

        headers = {"type": "update_margin_mode"}
        response = await self.post("/account/margin", data=data, headers=headers)

        return {
            "status": "ok" if response.get("success") else "err",
            "response": {
                "type": "updateMarginMode",
                "data": response
            }
        }

    async def batch_update_leverage(self, updates: List[Dict[str, Any]]) -> List[Dict]:
        """
        Update leverage for multiple symbols in parallel.
        New optimized method for batch leverage updates.

        Args:
            updates: List of dicts with keys: name, leverage, is_cross

        Returns:
            List of update responses
        """
        tasks = [
            self.update_leverage(u["leverage"], u["name"], u.get("is_cross", True))
            for u in updates
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        responses = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Failed to update leverage for {updates[i]['coin']}: {result}")
                responses.append({
                    "status": "err",
                    "error": str(result),
                    "coin": updates[i]["coin"]
                })
            else:
                responses.append(result)

        return responses

    async def cancel_all_orders(self, coins: Optional[List[str]] = None) -> Dict:
        """
        Cancel all open orders, optionally filtered by coins.
        Fetches open orders and cancels them all in parallel.

        Args:
            coins: Optional list of coins to filter cancellations

        Returns:
            Batch cancel response
        """
        # Import InfoAsyncAPI to get open orders
        from .info_async import InfoAsyncAPI

        info_api = InfoAsyncAPI(
            auth=self.auth,
            base_url=self.base_url,
            timeout=self.timeout.total if hasattr(self.timeout, 'total') else 30
        )

        try:
            # Get all open orders
            open_orders = await info_api.open_orders()

            # Filter by coins if specified
            cancels = []
            for order in open_orders:
                if coins is None or order.get("coin") in coins:
                    cancels.append({
                        "coin": order.get("coin"),
                        "oid": order.get("oid")
                    })

            # Cancel all in parallel
            if cancels:
                return await self.batch_cancel(cancels)
            else:
                return {
                    "status": "ok",
                    "response": {
                        "type": "batchCancel",
                        "data": {"statuses": [], "message": "No orders to cancel"}
                    }
                }

        finally:
            await info_api.close()

    async def place_and_cancel(
        self,
        new_orders: List[Dict],
        cancel_orders: List[Dict]
    ) -> Dict:
        """
        Place new orders and cancel existing orders in parallel.
        Optimized method for order replacement strategies.

        Args:
            new_orders: List of new orders to place
            cancel_orders: List of orders to cancel

        Returns:
            Combined response with both operations
        """
        # Create tasks for both operations
        tasks = []

        if new_orders:
            tasks.append(self.batch_orders(new_orders))
        else:
            tasks.append(asyncio.create_task(asyncio.coroutine(lambda: {"status": "ok", "response": {"data": {"statuses": []}}})()))

        if cancel_orders:
            tasks.append(self.batch_cancel(cancel_orders))
        else:
            tasks.append(asyncio.create_task(asyncio.coroutine(lambda: {"status": "ok", "response": {"data": {"statuses": []}}})()))

        # Execute both in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        place_result = results[0] if not isinstance(results[0], Exception) else {
            "status": "err",
            "error": str(results[0])
        }

        cancel_result = results[1] if not isinstance(results[1], Exception) else {
            "status": "err",
            "error": str(results[1])
        }

        return {
            "status": "ok",
            "place_orders": place_result,
            "cancel_orders": cancel_result
        }

    async def update_isolated_margin(self, amount: float, name: str) -> Dict:
        """
        Update isolated margin (Hyperliquid-specific method).

        Args:
            amount: Amount to add (positive) or remove (negative)
            name: Symbol (Hyperliquid parameter)

        Returns:
            Update response
        """
        # Note: We would need to implement add_margin and remove_margin async methods
        # For now, using a placeholder that calls the standard order method
        # In practice, this would call the actual margin adjustment endpoints
        raise NotImplementedError("Margin adjustment methods need to be implemented in async version")

    async def market_open(
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
            limit_price = 0  # Or calculate based on current price + slippage

        return await self.order(
            name=name,
            is_buy=is_buy,
            sz=sz,
            limit_px=limit_price,
            order_type=order_type,
            reduce_only=False,
            cloid=cloid,
            builder=builder
        )

    async def market_close(
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

        # If px provided, it's a limit order with IOC
        if px:
            order_type = {"limit": {"tif": "Ioc"}}
            limit_price = px
        else:
            order_type = {"market": {}}
            limit_price = 0

        # Map 'coin' to 'name' for internal call
        return await self.order(
            name=coin,  # Map 'coin' parameter to 'name'
            is_buy=False,  # This needs to be determined from position
            sz=sz or 0,  # If sz is None, need to get position size
            limit_px=limit_price,
            order_type=order_type,
            reduce_only=True,
            cloid=cloid,
            builder=builder
        )