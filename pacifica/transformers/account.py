"""
Account and position response transformers - Hyperliquid-compatible format
"""

from typing import Dict, Any, List, Optional


class AccountTransformer:
    """Transform account-related responses to exact Hyperliquid format"""

    @classmethod
    def transform_user_state(cls, account_response: Dict, positions_response: Dict) -> Dict:
        """
        Transform Pacifica account and positions to exact Hyperliquid user state format.

        Hyperliquid format:
        {
            "assetPositions": [...],
            "crossMaintenanceMarginUsed": str,
            "crossMarginSummary": {...},
            "marginSummary": {...},
            "withdrawable": str
        }
        """
        account = account_response.get("data", {})
        positions = positions_response.get("data", [])

        # Transform each position to Hyperliquid format
        asset_positions = []
        for pos in positions:
            # Determine signed size (positive for long, negative for short)
            if pos["side"] == "bid":
                szi = pos["amount"]
            else:  # ask/short
                szi = f"-{pos['amount']}"

            # Calculate position value
            position_value = abs(float(pos["amount"]) * float(pos["entry_price"]))

            # Build the position object in exact Hyperliquid format
            position_obj = {
                "position": {
                    "coin": pos["symbol"],
                    "entryPx": pos["entry_price"],
                    "leverage": {
                        "type": "cross" if not pos.get("isolated", False) else "isolated",
                        "value": pos.get("leverage", 20),  # Default leverage if not provided
                        "rawUsd": pos.get("margin", "0") if pos.get("isolated", False) else None
                    },
                    "liquidationPx": pos.get("liquidation_price", None),
                    "marginUsed": pos.get("margin", "0"),
                    "maxTradeSz": pos.get("max_trade_size", "0"),
                    "positionValue": str(position_value),
                    "returnOnEquity": pos.get("roe", "0"),
                    "szi": szi,
                    "unrealizedPnl": pos.get("unrealized_pnl", "0")
                }
            }

            # Add leverage if it was discovered (from our optimization)
            if "leverage" in pos:
                position_obj["position"]["leverage"] = {
                    "type": "cross" if not pos.get("isolated", False) else "isolated",
                    "value": pos["leverage"],
                    "rawUsd": pos.get("margin", "0") if pos.get("isolated", False) else None
                }

            asset_positions.append(position_obj)

        # Build the exact Hyperliquid response structure
        return {
            "assetPositions": asset_positions,
            "crossMaintenanceMarginUsed": account.get("cross_mmr", "0"),
            "crossMarginSummary": {
                "accountValue": account.get("account_equity", "0"),
                "totalMarginUsed": account.get("total_margin_used", "0"),
                "totalNtlPos": str(sum(
                    abs(float(p["amount"]) * float(p["entry_price"]))
                    for p in positions
                )) if positions else "0",
                "totalRawUsd": account.get("balance", "0")
            },
            "marginSummary": {
                "accountValue": account.get("account_equity", "0"),
                "totalMarginUsed": account.get("total_margin_used", "0"),
                "totalNtlPos": str(sum(
                    abs(float(p["amount"]) * float(p["entry_price"]))
                    for p in positions
                )) if positions else "0",
                "totalRawUsd": account.get("balance", "0"),
                "withdrawable": account.get("available_to_withdraw", "0")
            },
            "withdrawable": account.get("available_to_withdraw", "0")
        }

    @classmethod
    def transform_open_orders(cls, orders_response: Dict) -> List[Dict]:
        """
        Transform Pacifica open orders to exact Hyperliquid format.

        Hyperliquid format:
        [
            {
                "coin": str,
                "limitPx": str,
                "oid": int,
                "origSz": str,
                "side": str,  # "B" or "A"
                "sz": str,
                "timestamp": int,
                "cloid": str
            }
        ]
        """
        orders = orders_response.get("data", [])
        transformed = []

        for order in orders:
            transformed.append({
                "coin": order["symbol"],
                "limitPx": order.get("initial_price", order.get("price", "0")),
                "oid": order["order_id"],
                "origSz": order.get("amount", order.get("initial_amount", "0")),
                "side": "B" if order["side"] == "bid" else "A",
                "sz": order.get("remaining_amount", order.get("amount", "0")),  # Remaining size
                "timestamp": order["created_at"],
                "cloid": order.get("client_order_id")
            })

        return transformed

    @classmethod
    def transform_user_fills(cls, trades_response: Dict, oid: Optional[int] = None) -> List[Dict]:
        """
        Transform Pacifica trades history to exact Hyperliquid fills format.

        Hyperliquid format:
        [
            {
                "coin": str,
                "px": str,
                "sz": str,
                "side": str,  # "B" or "A"
                "time": int,
                "startPosition": str,
                "dir": str,
                "closedPnl": str,
                "hash": str,
                "oid": int,
                "crossed": bool,
                "fee": str,
                "tid": int,
                "liquidation": bool,
                "cloid": str
            }
        ]
        """
        trades = trades_response.get("data", [])
        transformed = []

        for trade in trades:
            # Filter by order ID if provided
            if oid and trade.get("order_id") != oid:
                continue

            # Determine side (B for buy, A for sell)
            if trade["side"] in ["bid", "long_open", "short_close"]:
                side = "B"
            else:  # ask, short_open, long_close
                side = "A"

            # Determine direction
            if "open" in trade.get("side", ""):
                dir_str = "Open"
            elif "close" in trade.get("side", ""):
                dir_str = "Close"
            else:
                dir_str = "Trade"

            transformed.append({
                "coin": trade["symbol"],
                "px": trade["price"],
                "sz": trade["amount"],
                "side": side,
                "time": trade["created_at"],
                "startPosition": trade.get("start_position", "0"),
                "dir": dir_str,
                "closedPnl": trade.get("pnl", "0"),
                "hash": trade.get("tx_hash", ""),
                "oid": trade.get("order_id"),
                "crossed": trade.get("event_type") == "fulfill_taker",  # True if taker
                "fee": trade.get("fee", "0"),
                "tid": trade.get("history_id"),
                "liquidation": trade.get("is_liquidation", False),
                "cloid": trade.get("client_order_id")
            })

        return transformed

    @classmethod
    def transform_all_mids(cls, prices_response: Dict) -> Dict[str, str]:
        """
        Transform Pacifica prices to Hyperliquid all_mids format.

        Hyperliquid format:
        {
            "BTC": "67890.5",
            "ETH": "3456.78",
            ...
        }
        """
        prices = prices_response.get("data", [])
        mids = {}

        for price_data in prices:
            symbol = price_data.get("symbol")
            if symbol:
                # Calculate mid price from bid/ask or use provided mid
                if "mid_price" in price_data:
                    mid = price_data["mid_price"]
                elif "bid" in price_data and "ask" in price_data:
                    bid = float(price_data["bid"])
                    ask = float(price_data["ask"])
                    mid = str((bid + ask) / 2)
                else:
                    mid = price_data.get("price", "0")

                mids[symbol] = mid

        return mids

    @classmethod
    def transform_meta(cls, markets_response: Dict) -> Dict:
        """
        Transform Pacifica market info to Hyperliquid meta format.

        Hyperliquid format:
        {
            "universe": [
                {
                    "name": str,
                    "szDecimals": int,
                    "maxLeverage": int,
                    "onlyIsolated": bool,
                    "marginMode": str,
                    "dex": str,
                    "normalized_name": str
                }
            ]
        }
        """
        markets = markets_response.get("data", [])
        universe = []

        for market in markets:
            # Determine if isolated only
            isolated_only = market.get("isolated_only", False)

            universe.append({
                "name": market.get("symbol", ""),
                "szDecimals": market.get("size_decimals", 8),
                "maxLeverage": market.get("max_leverage", market.get("maxLeverage", 50)),
                "onlyIsolated": isolated_only,
                "marginMode": "isolated" if isolated_only else "cross",
                "dex": "pacifica",
                "normalized_name": market.get("symbol", "").upper()
            })

        return {"universe": universe}

    @classmethod
    def transform_l2_book(cls, book_response: Dict) -> Dict:
        """
        Transform Pacifica order book to Hyperliquid L2 book format.

        Hyperliquid format:
        {
            "coin": str,
            "levels": [
                [
                    {"n": int, "px": str, "sz": str},  # bids
                    {"n": int, "px": str, "sz": str}   # asks
                ]
            ],
            "time": int
        }
        """
        book_data = book_response.get("data", {})

        # Transform bid and ask levels
        bid_levels = []
        ask_levels = []

        for i, bid in enumerate(book_data.get("bids", [])):
            bid_levels.append({
                "n": i + 1,
                "px": bid.get("price", "0"),
                "sz": bid.get("size", "0")
            })

        for i, ask in enumerate(book_data.get("asks", [])):
            ask_levels.append({
                "n": i + 1,
                "px": ask.get("price", "0"),
                "sz": ask.get("size", "0")
            })

        return {
            "coin": book_data.get("symbol", ""),
            "levels": [[bid_levels, ask_levels]],
            "time": book_data.get("timestamp", 0)
        }

    @classmethod
    def transform_user_funding(cls, funding_response: Dict) -> List[Dict]:
        """
        Transform Pacifica funding history to Hyperliquid format.

        Hyperliquid format:
        [
            {
                "coin": str,
                "fundingRate": str,
                "szi": str,
                "type": str,
                "time": int,
                "hash": str,
                "usdc": str
            }
        ]
        """
        fundings = funding_response.get("data", [])
        transformed = []

        for funding in fundings:
            transformed.append({
                "coin": funding.get("symbol", ""),
                "fundingRate": funding.get("funding_rate", "0"),
                "szi": funding.get("position_size", "0"),
                "type": "funding",
                "time": funding.get("timestamp", 0),
                "hash": funding.get("tx_hash", ""),
                "usdc": funding.get("funding_amount", "0")
            })

        return transformed

    @classmethod
    def transform_user_rate_limit(cls, rate_limit_response: Dict) -> Dict:
        """
        Transform rate limit response to Hyperliquid format.

        Hyperliquid format:
        {
            "nRequestsUsed": int,
            "nRequestsCap": int,
            "resetTime": int
        }
        """
        data = rate_limit_response.get("data", {})
        return {
            "nRequestsUsed": data.get("requests_used", 0),
            "nRequestsCap": data.get("requests_cap", 1000),
            "resetTime": data.get("reset_time", 0)
        }