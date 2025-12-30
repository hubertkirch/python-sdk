"""
Tests for base transformer functionality
"""

import pytest
from pacifica.transformers.base import ResponseTransformer


class TestToDecimal:
    """Tests for ResponseTransformer.to_decimal()"""

    def test_string_input(self):
        """String values should pass through as-is"""
        assert ResponseTransformer.to_decimal("123.45") == "123.45"
        assert ResponseTransformer.to_decimal("0") == "0"
        assert ResponseTransformer.to_decimal("-99.99") == "-99.99"

    def test_float_input(self):
        """Float values should be converted to string"""
        assert ResponseTransformer.to_decimal(123.45) == "123.45"
        assert ResponseTransformer.to_decimal(0.0) == "0.0"
        assert ResponseTransformer.to_decimal(-99.99) == "-99.99"

    def test_int_input(self):
        """Integer values should be converted to string"""
        assert ResponseTransformer.to_decimal(100) == "100"
        assert ResponseTransformer.to_decimal(0) == "0"
        assert ResponseTransformer.to_decimal(-50) == "-50"

    def test_none_input(self):
        """None should return None"""
        assert ResponseTransformer.to_decimal(None) is None


class TestTransformSide:
    """Tests for ResponseTransformer.transform_side()"""

    def test_position_context(self):
        """Position context should always return 'bid'"""
        assert ResponseTransformer.transform_side("bid", "position") == "bid"
        assert ResponseTransformer.transform_side("ask", "position") == "bid"
        assert ResponseTransformer.transform_side("anything", "position") == "bid"

    def test_trade_context_long(self):
        """Trade context with long positions should return 'B'"""
        assert ResponseTransformer.transform_side("long", "trade") == "B"
        assert ResponseTransformer.transform_side("open_long", "trade") == "B"
        assert ResponseTransformer.transform_side("close_long", "trade") == "B"
        assert ResponseTransformer.transform_side("LONG", "trade") == "B"
        assert ResponseTransformer.transform_side("bid", "trade") == "B"

    def test_trade_context_short(self):
        """Trade context with short positions should return 'S'"""
        assert ResponseTransformer.transform_side("short", "trade") == "S"
        assert ResponseTransformer.transform_side("open_short", "trade") == "S"
        assert ResponseTransformer.transform_side("close_short", "trade") == "S"
        assert ResponseTransformer.transform_side("ask", "trade") == "S"

    def test_order_context_bid(self):
        """Order context with bid should return 'B'"""
        assert ResponseTransformer.transform_side("bid", "order") == "B"

    def test_order_context_ask(self):
        """Order context with ask should return 'A'"""
        assert ResponseTransformer.transform_side("ask", "order") == "A"

    def test_unknown_context(self):
        """Unknown context should return original side"""
        assert ResponseTransformer.transform_side("bid", "unknown") == "bid"
        assert ResponseTransformer.transform_side("custom", "other") == "custom"

    def test_default_context_is_position(self):
        """Default context should be 'position'"""
        assert ResponseTransformer.transform_side("anything") == "bid"
