"""
Exchange/trading response transformers - Hyperliquid-compatible format
"""

from typing import Dict, Any, List, Optional


class ExchangeTransformer:
    """Transform exchange/trading responses to exact Hyperliquid format"""

    @classmethod
    def transform_order_response(cls, order_response: Dict) -> Dict:
        """
        Transform Pacifica order response to exact Hyperliquid format.

        Hyperliquid format:
        {
            "status": "ok",
            "response": {
                "type": "order",
                "data": {
                    "statuses": [
                        {
                            "filled": {...},
                            "resting": {...}
                        }
                    ]
                }
            }
        }
        """
        data = order_response.get("data", {})

        # Build Hyperliquid-compatible response
        return {
            "status": "ok" if order_response.get("success", True) else "error",
            "response": {
                "type": "order",
                "data": {
                    "statuses": [{
                        "filled": {
                            "totalSz": data.get("filled_amount", "0"),
                            "avgPx": data.get("avg_fill_price", "0")
                        },
                        "resting": {
                            "oid": data.get("order_id"),
                            "cloid": data.get("client_order_id")
                        }
                    }]
                }
            }
        }

    @classmethod
    def transform_cancel_response(cls, cancel_response: Dict) -> Dict:
        """
        Transform Pacifica cancel response to exact Hyperliquid format.

        Hyperliquid format:
        {
            "status": "ok",
            "response": {
                "type": "cancel",
                "data": {
                    "statuses": ["success"]
                }
            }
        }
        """
        success = cancel_response.get("success", True)

        return {
            "status": "ok" if success else "error",
            "response": {
                "type": "cancel",
                "data": {
                    "statuses": ["success"] if success else ["error"]
                }
            }
        }

    @classmethod
    def transform_bulk_orders_response(cls, bulk_response: Dict) -> Dict:
        """
        Transform Pacifica bulk orders response to exact Hyperliquid format.

        Hyperliquid format:
        {
            "status": "ok",
            "response": {
                "type": "bulk_orders",
                "data": [
                    {
                        "filled": {...},
                        "resting": {...}
                    }
                ]
            }
        }
        """
        orders = bulk_response.get("data", [])
        statuses = []

        for order in orders:
            statuses.append({
                "filled": {
                    "totalSz": order.get("filled_amount", "0"),
                    "avgPx": order.get("avg_fill_price", "0")
                },
                "resting": {
                    "oid": order.get("order_id"),
                    "cloid": order.get("client_order_id")
                }
            })

        return {
            "status": "ok" if bulk_response.get("success", True) else "error",
            "response": {
                "type": "bulk_orders",
                "data": statuses
            }
        }

    @classmethod
    def transform_update_leverage_response(cls, leverage_response: Dict) -> Dict:
        """
        Transform Pacifica update leverage response to exact Hyperliquid format.

        Hyperliquid format:
        {
            "status": "ok",
            "response": {
                "type": "update_leverage",
                "data": {}
            }
        }
        """
        return {
            "status": "ok" if leverage_response.get("success", True) else "error",
            "response": {
                "type": "update_leverage",
                "data": leverage_response.get("data", {})
            }
        }

    @classmethod
    def transform_update_margin_response(cls, margin_response: Dict) -> Dict:
        """
        Transform Pacifica update margin response to exact Hyperliquid format.

        Hyperliquid format:
        {
            "status": "ok",
            "response": {
                "type": "update_margin",
                "data": {}
            }
        }
        """
        return {
            "status": "ok" if margin_response.get("success", True) else "error",
            "response": {
                "type": "update_margin",
                "data": margin_response.get("data", {})
            }
        }

    @classmethod
    def transform_twap_response(cls, twap_response: Dict) -> Dict:
        """
        Transform Pacifica TWAP response to standardized format.

        Note: TWAP is Pacifica-specific, not in Hyperliquid
        """
        return {
            "status": "ok" if twap_response.get("success", True) else "error",
            "response": {
                "type": "twap_order",
                "data": {
                    "twap_id": twap_response.get("data", {}).get("twap_id"),
                    "status": twap_response.get("data", {}).get("status", "created")
                }
            }
        }

    @classmethod
    def transform_modify_order_response(cls, modify_response: Dict) -> Dict:
        """
        Transform Pacifica modify order response to exact Hyperliquid format.

        Hyperliquid format:
        {
            "status": "ok",
            "response": {
                "type": "modify",
                "data": {
                    "oid": int,
                    "cloid": str
                }
            }
        }
        """
        data = modify_response.get("data", {})

        return {
            "status": "ok" if modify_response.get("success", True) else "error",
            "response": {
                "type": "modify",
                "data": {
                    "oid": data.get("order_id"),
                    "cloid": data.get("client_order_id")
                }
            }
        }

    @classmethod
    def transform_error_response(cls, error_msg: str) -> Dict:
        """
        Create standardized error response in Hyperliquid format.

        Hyperliquid format:
        {
            "status": "error",
            "response": {
                "type": "error",
                "data": {
                    "msg": str
                }
            }
        }
        """
        return {
            "status": "error",
            "response": {
                "type": "error",
                "data": {
                    "msg": error_msg
                }
            }
        }