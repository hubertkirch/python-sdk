"""
Market data response transformers
"""

from typing import Dict, Any, List, Optional
from .base import ResponseTransformer


class MarketTransformer(ResponseTransformer):
    """Transform market data responses to Hyperliquid format"""

    @classmethod
    def transform_meta(cls, info_response: Dict) -> Dict:
        """Transform Pacifica market info to Hyperliquid meta format"""
        markets = info_response.get("data", [])
        universe = []

        for market in markets:
            universe.append({
                "name": market["symbol"],
                "szDecimals": market.get("size_decimals", 8),
                "maxLeverage": market.get("max_leverage", 100),
                "onlyIsolated": market.get("isolated_only", False),
                "lotSize": market.get("lot_size", "0.00001"),
                "tickSize": market.get("tick_size", "0.01"),
                "minTick": market.get("min_tick", "0"),
                "maxTick": market.get("max_tick", "1000000"),
                "minOrderSize": market.get("min_order_size", "10"),
                "maxOrderSize": market.get("max_order_size", "5000000"),
                "fundingRate": market.get("funding_rate", "0"),
                "nextFundingRate": market.get("next_funding_rate", "0"),
                "createdAt": market.get("created_at")
            })

        return {"universe": universe}

    @classmethod
    def transform_all_mids(cls, prices_response: Dict) -> Dict:
        """Transform Pacifica prices to Hyperliquid all mids format"""
        prices = prices_response.get("data", [])
        mids = {}

        for price_data in prices:
            mids[price_data["symbol"]] = price_data.get("mid", "0")

        return mids

    @classmethod
    def transform_l2_book(cls, book_response: Dict) -> Dict:
        """Transform Pacifica orderbook to Hyperliquid L2 book format"""
        book = book_response.get("data", {})

        levels = []
        for bid in book.get("bids", []):
            levels.append({
                "px": bid[0],
                "sz": bid[1],
                "n": 1
            })

        for ask in book.get("asks", []):
            levels.append({
                "px": ask[0],
                "sz": ask[1],
                "n": 1
            })

        return {
            "coin": book.get("symbol", ""),
            "levels": [levels],
            "time": book.get("timestamp", 0)
        }

    @classmethod
    def transform_candles(cls, candles_response: Dict, coin: str, interval: str) -> List[Dict]:
        """Transform Pacifica candles to Hyperliquid format"""
        candles = candles_response.get("data", [])
        transformed = []

        for candle in candles:
            transformed.append({
                "T": candle.get("timestamp", 0),
                "c": candle.get("close", "0"),
                "h": candle.get("high", "0"),
                "l": candle.get("low", "0"),
                "o": candle.get("open", "0"),
                "v": candle.get("volume", "0"),
                "s": coin,
                "i": interval,
                "n": candle.get("trades_count", 0)
            })

        return transformed

    @classmethod
    def transform_funding_rates(cls, funding_response: Dict) -> List[Dict]:
        """Transform Pacifica funding rates to Hyperliquid format"""
        funding_data = funding_response.get("data", [])
        transformed = []

        for funding in funding_data:
            transformed.append({
                "coin": funding.get("symbol", ""),
                "fundingRate": funding.get("funding_rate", "0"),
                "premium": funding.get("premium", "0"),
                "time": funding.get("next_funding_time", 0)
            })

        return transformed

    @classmethod
    def transform_open_interest(cls, oi_response: Dict) -> Dict:
        """Transform Pacifica open interest to Hyperliquid format"""
        oi_data = oi_response.get("data", [])
        result = {}

        for item in oi_data:
            result[item["symbol"]] = {
                "oi": item.get("open_interest", "0"),
                "oiValue": item.get("open_interest_value", "0")
            }

        return result