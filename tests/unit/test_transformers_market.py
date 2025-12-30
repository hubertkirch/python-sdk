"""
Tests for market transformer functionality
"""

import pytest
from pacifica.transformers.market import MarketTransformer


class TestTransformMeta:
    """Tests for MarketTransformer.transform_meta()"""

    def test_basic_transformation(self, sample_markets_response):
        """Test basic meta transformation"""
        result = MarketTransformer.transform_meta(sample_markets_response)

        assert "universe" in result
        assert len(result["universe"]) == 2

    def test_market_fields(self, sample_markets_response):
        """Test all expected market fields are present"""
        result = MarketTransformer.transform_meta(sample_markets_response)

        market = result["universe"][0]
        expected_fields = [
            "name", "szDecimals", "maxLeverage", "onlyIsolated",
            "lotSize", "tickSize", "minTick", "maxTick",
            "minOrderSize", "maxOrderSize", "fundingRate",
            "nextFundingRate", "createdAt"
        ]
        for field in expected_fields:
            assert field in market, f"Missing field: {field}"

    def test_market_values(self, sample_markets_response):
        """Test market values are correctly mapped"""
        result = MarketTransformer.transform_meta(sample_markets_response)

        btc = result["universe"][0]
        assert btc["name"] == "BTC"
        assert btc["szDecimals"] == 6
        assert btc["maxLeverage"] == 100
        assert btc["onlyIsolated"] is False
        assert btc["lotSize"] == "0.0001"
        assert btc["tickSize"] == "0.1"
        assert btc["minOrderSize"] == "10"
        assert btc["maxOrderSize"] == "10000000"
        assert btc["fundingRate"] == "0.0001"
        assert btc["nextFundingRate"] == "0.00012"
        assert btc["createdAt"] == 1690000000000

    def test_isolated_only_market(self, sample_markets_response):
        """Test isolated-only market mapping"""
        result = MarketTransformer.transform_meta(sample_markets_response)

        eth = result["universe"][1]
        assert eth["name"] == "ETH"
        assert eth["onlyIsolated"] is True

    def test_default_values(self):
        """Test default values when fields are missing"""
        response = {
            "data": [
                {"symbol": "NEW"}
            ]
        }

        result = MarketTransformer.transform_meta(response)

        market = result["universe"][0]
        assert market["name"] == "NEW"
        assert market["szDecimals"] == 8  # Default
        assert market["maxLeverage"] == 100  # Default
        assert market["onlyIsolated"] is False  # Default

    def test_empty_markets(self):
        """Test empty markets list"""
        response = {"data": []}

        result = MarketTransformer.transform_meta(response)

        assert result["universe"] == []


class TestTransformAllMids:
    """Tests for MarketTransformer.transform_all_mids()"""

    def test_basic_transformation(self, sample_prices_response):
        """Test basic price transformation"""
        result = MarketTransformer.transform_all_mids(sample_prices_response)

        assert result["BTC"] == "50000.50"
        assert result["ETH"] == "3000.25"
        assert result["SOL"] == "100.10"

    def test_empty_prices(self):
        """Test empty prices list"""
        response = {"data": []}

        result = MarketTransformer.transform_all_mids(response)

        assert result == {}

    def test_default_mid_value(self):
        """Test default value when mid is missing"""
        response = {
            "data": [
                {"symbol": "BTC"}
            ]
        }

        result = MarketTransformer.transform_all_mids(response)

        assert result["BTC"] == "0"


class TestTransformL2Book:
    """Tests for MarketTransformer.transform_l2_book()"""

    def test_basic_transformation(self, sample_orderbook_response):
        """Test basic orderbook transformation"""
        result = MarketTransformer.transform_l2_book(sample_orderbook_response)

        assert result["coin"] == "BTC"
        assert result["time"] == 1700000000000
        assert "levels" in result

    def test_levels_structure(self, sample_orderbook_response):
        """Test levels structure"""
        result = MarketTransformer.transform_l2_book(sample_orderbook_response)

        # Levels should be a list with one element containing all levels
        assert len(result["levels"]) == 1
        # Total levels = 3 bids + 3 asks = 6
        assert len(result["levels"][0]) == 6

    def test_bid_level_fields(self, sample_orderbook_response):
        """Test bid level transformation"""
        result = MarketTransformer.transform_l2_book(sample_orderbook_response)

        # First level should be first bid
        level = result["levels"][0][0]
        assert level["px"] == "49990.00"
        assert level["sz"] == "1.5"
        assert level["n"] == 1

    def test_ask_level_fields(self, sample_orderbook_response):
        """Test ask level transformation"""
        result = MarketTransformer.transform_l2_book(sample_orderbook_response)

        # Fourth level should be first ask (after 3 bids)
        level = result["levels"][0][3]
        assert level["px"] == "50010.00"
        assert level["sz"] == "1.2"
        assert level["n"] == 1

    def test_empty_orderbook(self):
        """Test empty orderbook"""
        response = {
            "data": {
                "symbol": "BTC",
                "bids": [],
                "asks": [],
                "timestamp": 1700000000000
            }
        }

        result = MarketTransformer.transform_l2_book(response)

        assert result["coin"] == "BTC"
        assert result["levels"] == [[]]

    def test_missing_data(self):
        """Test handling of missing data field"""
        response = {"data": {}}

        result = MarketTransformer.transform_l2_book(response)

        assert result["coin"] == ""
        assert result["time"] == 0


class TestTransformCandles:
    """Tests for MarketTransformer.transform_candles()"""

    def test_basic_transformation(self, sample_candles_response):
        """Test basic candles transformation"""
        result = MarketTransformer.transform_candles(
            sample_candles_response,
            coin="BTC",
            interval="1h"
        )

        assert len(result) == 2

    def test_candle_fields(self, sample_candles_response):
        """Test all expected candle fields are present"""
        result = MarketTransformer.transform_candles(
            sample_candles_response,
            coin="BTC",
            interval="1h"
        )

        candle = result[0]
        assert "T" in candle  # Timestamp
        assert "o" in candle  # Open
        assert "h" in candle  # High
        assert "l" in candle  # Low
        assert "c" in candle  # Close
        assert "v" in candle  # Volume
        assert "s" in candle  # Symbol
        assert "i" in candle  # Interval
        assert "n" in candle  # Trades count

    def test_candle_values(self, sample_candles_response):
        """Test candle values are correctly mapped"""
        result = MarketTransformer.transform_candles(
            sample_candles_response,
            coin="BTC",
            interval="1h"
        )

        candle = result[0]
        assert candle["T"] == 1700000000000
        assert candle["o"] == "49000.00"
        assert candle["h"] == "50500.00"
        assert candle["l"] == "48500.00"
        assert candle["c"] == "50000.00"
        assert candle["v"] == "1234.56"
        assert candle["s"] == "BTC"
        assert candle["i"] == "1h"
        assert candle["n"] == 5000

    def test_coin_and_interval_passed_through(self, sample_candles_response):
        """Test that coin and interval are added to each candle"""
        result = MarketTransformer.transform_candles(
            sample_candles_response,
            coin="ETH",
            interval="4h"
        )

        for candle in result:
            assert candle["s"] == "ETH"
            assert candle["i"] == "4h"

    def test_empty_candles(self):
        """Test empty candles list"""
        response = {"data": []}

        result = MarketTransformer.transform_candles(
            response,
            coin="BTC",
            interval="1h"
        )

        assert result == []

    def test_default_values(self):
        """Test default values when candle fields are missing"""
        response = {
            "data": [
                {"timestamp": 1700000000000}
            ]
        }

        result = MarketTransformer.transform_candles(
            response,
            coin="BTC",
            interval="1h"
        )

        candle = result[0]
        assert candle["T"] == 1700000000000
        assert candle["o"] == "0"
        assert candle["h"] == "0"
        assert candle["l"] == "0"
        assert candle["c"] == "0"
        assert candle["v"] == "0"
        assert candle["n"] == 0


class TestTransformFundingRates:
    """Tests for MarketTransformer.transform_funding_rates()"""

    def test_basic_transformation(self, sample_funding_rates_response):
        """Test basic funding rates transformation"""
        result = MarketTransformer.transform_funding_rates(
            sample_funding_rates_response
        )

        assert len(result) == 2

    def test_funding_rate_fields(self, sample_funding_rates_response):
        """Test all expected fields are present"""
        result = MarketTransformer.transform_funding_rates(
            sample_funding_rates_response
        )

        rate = result[0]
        assert "coin" in rate
        assert "fundingRate" in rate
        assert "premium" in rate
        assert "time" in rate

    def test_funding_rate_values(self, sample_funding_rates_response):
        """Test funding rate values are correctly mapped"""
        result = MarketTransformer.transform_funding_rates(
            sample_funding_rates_response
        )

        btc_rate = result[0]
        assert btc_rate["coin"] == "BTC"
        assert btc_rate["fundingRate"] == "0.0001"
        assert btc_rate["premium"] == "0.00005"
        assert btc_rate["time"] == 1700007200000

    def test_negative_funding_rate(self, sample_funding_rates_response):
        """Test negative funding rate handling"""
        result = MarketTransformer.transform_funding_rates(
            sample_funding_rates_response
        )

        eth_rate = result[1]
        assert eth_rate["fundingRate"] == "-0.0002"
        assert eth_rate["premium"] == "-0.0001"

    def test_empty_funding_rates(self):
        """Test empty funding rates list"""
        response = {"data": []}

        result = MarketTransformer.transform_funding_rates(response)

        assert result == []

    def test_default_values(self):
        """Test default values when fields are missing"""
        response = {
            "data": [
                {"symbol": "BTC"}
            ]
        }

        result = MarketTransformer.transform_funding_rates(response)

        rate = result[0]
        assert rate["coin"] == "BTC"
        assert rate["fundingRate"] == "0"
        assert rate["premium"] == "0"
        assert rate["time"] == 0


class TestTransformOpenInterest:
    """Tests for MarketTransformer.transform_open_interest()"""

    def test_basic_transformation(self, sample_open_interest_response):
        """Test basic open interest transformation"""
        result = MarketTransformer.transform_open_interest(
            sample_open_interest_response
        )

        assert "BTC" in result
        assert "ETH" in result

    def test_open_interest_fields(self, sample_open_interest_response):
        """Test all expected fields are present"""
        result = MarketTransformer.transform_open_interest(
            sample_open_interest_response
        )

        btc_oi = result["BTC"]
        assert "oi" in btc_oi
        assert "oiValue" in btc_oi

    def test_open_interest_values(self, sample_open_interest_response):
        """Test open interest values are correctly mapped"""
        result = MarketTransformer.transform_open_interest(
            sample_open_interest_response
        )

        assert result["BTC"]["oi"] == "15000.5"
        assert result["BTC"]["oiValue"] == "750000000"
        assert result["ETH"]["oi"] == "250000.0"
        assert result["ETH"]["oiValue"] == "750000000"

    def test_empty_open_interest(self):
        """Test empty open interest list"""
        response = {"data": []}

        result = MarketTransformer.transform_open_interest(response)

        assert result == {}

    def test_default_values(self):
        """Test default values when fields are missing"""
        response = {
            "data": [
                {"symbol": "BTC"}
            ]
        }

        result = MarketTransformer.transform_open_interest(response)

        assert result["BTC"]["oi"] == "0"
        assert result["BTC"]["oiValue"] == "0"
