"""
Base transformer for converting Pacifica responses to Hyperliquid format
"""

from typing import Dict, Any, List, Optional, Union
from decimal import Decimal


class ResponseTransformer:
    """Base class for response transformation"""

    @staticmethod
    def to_decimal(value: Union[str, float, int, None]) -> Optional[str]:
        """Convert any numeric type to string decimal"""
        if value is None:
            return None
        return str(value)

    @staticmethod
    def transform_side(side: str, context: str = "position") -> str:
        """
        Transform Pacifica side to Hyperliquid format.

        Pacifica -> Hyperliquid:
        - Position: "bid"/"ask" -> positive/negative szi
        - Trade: "open_long"/"close_long"/"open_short"/"close_short" -> "B"/"S"
        - Order: "bid"/"ask" -> "B"/"A"
        """
        if context == "position":
            return "bid"
        elif context == "trade":
            if "long" in side.lower() or side == "bid":
                return "B"
            else:
                return "S"
        elif context == "order":
            return "B" if side == "bid" else "A"
        return side