"""
Tests for account transformer functionality
"""

from pacifica.transformers.account import AccountTransformer


class TestTransformUserState:
    """Tests for AccountTransformer.transform_user_state()"""

    def test_basic_transformation(self, sample_account_response, sample_positions_response):
        """Test basic user state transformation with account and positions"""
        result = AccountTransformer.transform_user_state(
            sample_account_response,
            sample_positions_response
        )

        # Check top-level keys exist
        assert "assetPositions" in result
        assert "crossMaintenanceMarginUsed" in result
        assert "crossMarginSummary" in result
        assert "marginSummary" in result
        assert "withdrawable" in result

    def test_account_values(self, sample_account_response, sample_positions_response):
        """Test that account values are correctly mapped"""
        result = AccountTransformer.transform_user_state(
            sample_account_response,
            sample_positions_response
        )

        assert result["crossMaintenanceMarginUsed"] == "1200.25"
        assert result["withdrawable"] == "5000.00"
        assert result["crossMarginSummary"]["accountValue"] == "10000.50"
        assert result["crossMarginSummary"]["totalMarginUsed"] == "3500.50"
        assert result["crossMarginSummary"]["totalRawUsd"] == "8500.00"

    def test_margin_summary(self, sample_account_response, sample_positions_response):
        """Test marginSummary contains correct fields"""
        result = AccountTransformer.transform_user_state(
            sample_account_response,
            sample_positions_response
        )

        margin = result["marginSummary"]
        assert margin["accountValue"] == "10000.50"
        assert margin["totalMarginUsed"] == "3500.50"
        assert margin["withdrawable"] == "5000.00"
        assert margin["totalRawUsd"] == "8500.00"
        assert "totalNtlPos" in margin

    def test_position_count(self, sample_account_response, sample_positions_response):
        """Test correct number of positions are transformed"""
        result = AccountTransformer.transform_user_state(
            sample_account_response,
            sample_positions_response
        )

        assert len(result["assetPositions"]) == 2

    def test_long_position_transformation(self, sample_account_response, sample_positions_response):
        """Test long (bid) position has positive szi"""
        result = AccountTransformer.transform_user_state(
            sample_account_response,
            sample_positions_response
        )

        btc_position = result["assetPositions"][0]["position"]
        assert btc_position["coin"] == "BTC"
        assert btc_position["szi"] == "0.5"  # Positive for long
        assert btc_position["entryPx"] == "50000.00"
        assert btc_position["leverage"]["type"] == "cross"
        assert btc_position["leverage"]["value"] == 10

    def test_short_position_transformation(self, sample_account_response, sample_positions_response):
        """Test short (ask) position has negative szi"""
        result = AccountTransformer.transform_user_state(
            sample_account_response,
            sample_positions_response
        )

        eth_position = result["assetPositions"][1]["position"]
        assert eth_position["coin"] == "ETH"
        assert eth_position["szi"] == "-2.0"  # Negative for short
        assert eth_position["entryPx"] == "3000.00"
        assert eth_position["leverage"]["type"] == "isolated"
        assert eth_position["leverage"]["value"] == 5

    def test_isolated_position_has_raw_usd(self, sample_account_response, sample_positions_response):
        """Test isolated position includes rawUsd in leverage"""
        result = AccountTransformer.transform_user_state(
            sample_account_response,
            sample_positions_response
        )

        eth_position = result["assetPositions"][1]["position"]
        assert eth_position["leverage"]["rawUsd"] == "1200.00"

    def test_cross_position_no_raw_usd(self, sample_account_response, sample_positions_response):
        """Test cross position has None for rawUsd"""
        result = AccountTransformer.transform_user_state(
            sample_account_response,
            sample_positions_response
        )

        btc_position = result["assetPositions"][0]["position"]
        assert btc_position["leverage"]["rawUsd"] is None

    def test_position_value_calculation(self, sample_account_response, sample_positions_response):
        """Test position value is calculated correctly"""
        result = AccountTransformer.transform_user_state(
            sample_account_response,
            sample_positions_response
        )

        # BTC: 0.5 * 50000 = 25000
        btc_position = result["assetPositions"][0]["position"]
        assert btc_position["positionValue"] == "25000.0"

        # ETH: 2.0 * 3000 = 6000
        eth_position = result["assetPositions"][1]["position"]
        assert eth_position["positionValue"] == "6000.0"

    def test_total_notional_position(self, sample_account_response, sample_positions_response):
        """Test totalNtlPos is sum of all position values"""
        result = AccountTransformer.transform_user_state(
            sample_account_response,
            sample_positions_response
        )

        # 25000 + 6000 = 31000
        assert result["crossMarginSummary"]["totalNtlPos"] == "31000.0"

    def test_empty_positions(self, sample_account_response, empty_positions_response):
        """Test handling of empty positions list"""
        result = AccountTransformer.transform_user_state(
            sample_account_response,
            empty_positions_response
        )

        assert result["assetPositions"] == []
        assert result["crossMarginSummary"]["totalNtlPos"] == "0"
        assert result["marginSummary"]["totalNtlPos"] == "0"

    def test_empty_account(self, empty_account_response, empty_positions_response):
        """Test handling of empty/new account"""
        result = AccountTransformer.transform_user_state(
            empty_account_response,
            empty_positions_response
        )

        assert result["assetPositions"] == []
        assert result["crossMaintenanceMarginUsed"] == "0"
        assert result["withdrawable"] == "0"
        assert result["crossMarginSummary"]["accountValue"] == "0"


class TestTransformOpenOrders:
    """Tests for AccountTransformer.transform_open_orders()"""

    def test_basic_transformation(self, sample_orders_response):
        """Test basic order transformation"""
        result = AccountTransformer.transform_open_orders(sample_orders_response)

        assert len(result) == 2

    def test_order_fields(self, sample_orders_response):
        """Test all expected fields are present"""
        result = AccountTransformer.transform_open_orders(sample_orders_response)

        order = result[0]
        assert "coin" in order
        assert "limitPx" in order
        assert "oid" in order
        assert "origSz" in order
        assert "side" in order
        assert "sz" in order
        assert "timestamp" in order
        assert "cloid" in order

    def test_bid_order_side(self, sample_orders_response):
        """Test bid order has side 'B'"""
        result = AccountTransformer.transform_open_orders(sample_orders_response)

        btc_order = result[0]
        assert btc_order["coin"] == "BTC"
        assert btc_order["side"] == "B"

    def test_ask_order_side(self, sample_orders_response):
        """Test ask order has side 'A'"""
        result = AccountTransformer.transform_open_orders(sample_orders_response)

        eth_order = result[1]
        assert eth_order["coin"] == "ETH"
        assert eth_order["side"] == "A"

    def test_order_values(self, sample_orders_response):
        """Test order values are correctly mapped"""
        result = AccountTransformer.transform_open_orders(sample_orders_response)

        order = result[0]
        assert order["oid"] == 12345
        assert order["limitPx"] == "48000.00"
        assert order["origSz"] == "0.5"
        assert order["sz"] == "0.3"  # Remaining amount
        assert order["timestamp"] == 1700000000000
        assert order["cloid"] == "client-order-1"

    def test_null_cloid(self, sample_orders_response):
        """Test order with null client order ID"""
        result = AccountTransformer.transform_open_orders(sample_orders_response)

        eth_order = result[1]
        assert eth_order["cloid"] is None

    def test_empty_orders(self, empty_orders_response):
        """Test empty orders list"""
        result = AccountTransformer.transform_open_orders(empty_orders_response)

        assert result == []


class TestTransformUserFills:
    """Tests for AccountTransformer.transform_user_fills()"""

    def test_basic_transformation(self, sample_trades_response):
        """Test basic fills transformation"""
        result = AccountTransformer.transform_user_fills(sample_trades_response)

        assert len(result) == 2

    def test_fill_fields(self, sample_trades_response):
        """Test all expected fields are present"""
        result = AccountTransformer.transform_user_fills(sample_trades_response)

        fill = result[0]
        expected_fields = [
            "coin", "px", "sz", "side", "time", "startPosition",
            "dir", "closedPnl", "hash", "oid", "crossed", "fee",
            "tid", "liquidation", "cloid"
        ]
        for field in expected_fields:
            assert field in fill, f"Missing field: {field}"

    def test_long_open_side(self, sample_trades_response):
        """Test long_open trade has side 'B'"""
        result = AccountTransformer.transform_user_fills(sample_trades_response)

        btc_fill = result[0]
        assert btc_fill["side"] == "B"
        assert btc_fill["dir"] == "Open"

    def test_short_close_side(self, sample_trades_response):
        """Test short_close trade has side 'B' (buying to close)"""
        result = AccountTransformer.transform_user_fills(sample_trades_response)

        eth_fill = result[1]
        assert eth_fill["side"] == "B"  # short_close is a buy
        assert eth_fill["dir"] == "Close"

    def test_taker_crossed_flag(self, sample_trades_response):
        """Test taker fills have crossed=True"""
        result = AccountTransformer.transform_user_fills(sample_trades_response)

        # First trade is fulfill_taker
        assert result[0]["crossed"] is True
        # Second trade is fulfill_maker
        assert result[1]["crossed"] is False

    def test_fill_values(self, sample_trades_response):
        """Test fill values are correctly mapped"""
        result = AccountTransformer.transform_user_fills(sample_trades_response)

        fill = result[0]
        assert fill["coin"] == "BTC"
        assert fill["px"] == "49000.00"
        assert fill["sz"] == "0.2"
        assert fill["time"] == 1700000000000
        assert fill["fee"] == "9.80"
        assert fill["tid"] == 99001
        assert fill["hash"] == "0xabc123"

    def test_filter_by_oid(self, sample_trades_response):
        """Test filtering fills by order ID"""
        result = AccountTransformer.transform_user_fills(
            sample_trades_response,
            oid=12345
        )

        assert len(result) == 1
        assert result[0]["oid"] == 12345

    def test_filter_by_oid_no_match(self, sample_trades_response):
        """Test filtering with non-matching order ID"""
        result = AccountTransformer.transform_user_fills(
            sample_trades_response,
            oid=99999
        )

        assert result == []

    def test_liquidation_fill(self, sample_liquidation_trade):
        """Test liquidation flag is correctly set"""
        result = AccountTransformer.transform_user_fills(sample_liquidation_trade)

        assert len(result) == 1
        assert result[0]["liquidation"] is True


class TestTransformUserFunding:
    """Tests for AccountTransformer.transform_user_funding()"""

    def test_basic_transformation(self, sample_funding_response):
        """Test basic funding transformation"""
        result = AccountTransformer.transform_user_funding(sample_funding_response)

        assert len(result) == 2

    def test_funding_fields(self, sample_funding_response):
        """Test all expected fields are present"""
        result = AccountTransformer.transform_user_funding(sample_funding_response)

        funding = result[0]
        assert "coin" in funding
        assert "fundingRate" in funding
        assert "szi" in funding
        assert "type" in funding
        assert "time" in funding
        assert "hash" in funding
        assert "usdc" in funding

    def test_funding_values(self, sample_funding_response):
        """Test funding values are correctly mapped"""
        result = AccountTransformer.transform_user_funding(sample_funding_response)

        funding = result[0]
        assert funding["coin"] == "BTC"
        assert funding["fundingRate"] == "0.0001"
        assert funding["szi"] == "0.5"
        assert funding["type"] == "funding"
        assert funding["time"] == 1700000000000
        assert funding["hash"] == "0xfund123"
        assert funding["usdc"] == "2.50"

    def test_negative_funding(self, sample_funding_response):
        """Test negative funding rate handling"""
        result = AccountTransformer.transform_user_funding(sample_funding_response)

        eth_funding = result[1]
        assert eth_funding["fundingRate"] == "-0.0002"
        assert eth_funding["usdc"] == "-1.20"


class TestTransformNonFundingLedgerUpdates:
    """Tests for AccountTransformer.transform_non_funding_ledger_updates()"""

    def test_basic_transformation(self, sample_balance_events):
        """Test basic ledger transformation"""
        result = AccountTransformer.transform_non_funding_ledger_updates(
            sample_balance_events
        )

        # Should only include deposit, withdraw, transfer, deposit_release (4 events)
        # The "fee" event should be filtered out
        assert len(result) == 4

    def test_deposit_transformation(self, sample_balance_events):
        """Test deposit event transformation"""
        result = AccountTransformer.transform_non_funding_ledger_updates(
            sample_balance_events
        )

        deposit = result[0]
        assert deposit["delta"]["type"] == "deposit"
        assert deposit["delta"]["coin"] == "USDC"
        assert deposit["delta"]["usdc"] == "1000.00"
        assert deposit["hash"] == "0xdep001"
        assert deposit["time"] == 1699900000000

    def test_withdraw_transformation(self, sample_balance_events):
        """Test withdraw event transformation"""
        result = AccountTransformer.transform_non_funding_ledger_updates(
            sample_balance_events
        )

        withdraw = result[1]
        assert withdraw["delta"]["type"] == "withdraw"
        assert withdraw["delta"]["usdc"] == "500.00"

    def test_transfer_transformation(self, sample_balance_events):
        """Test subaccount transfer transformation"""
        result = AccountTransformer.transform_non_funding_ledger_updates(
            sample_balance_events
        )

        transfer = result[2]
        assert transfer["delta"]["type"] == "transfer"
        assert transfer["delta"]["usdc"] == "200.00"

    def test_deposit_release_transformation(self, sample_balance_events):
        """Test deposit_release maps to deposit type"""
        result = AccountTransformer.transform_non_funding_ledger_updates(
            sample_balance_events
        )

        release = result[3]
        assert release["delta"]["type"] == "deposit"

    def test_fee_event_filtered(self, sample_balance_events):
        """Test that fee events are filtered out"""
        result = AccountTransformer.transform_non_funding_ledger_updates(
            sample_balance_events
        )

        types = [r["delta"]["type"] for r in result]
        # Fee should not be in the result
        assert "fee" not in types

    def test_empty_events(self):
        """Test empty events list"""
        result = AccountTransformer.transform_non_funding_ledger_updates([])

        assert result == []


class TestTransformAllMids:
    """Tests for AccountTransformer.transform_all_mids()"""

    def test_with_mid_price(self):
        """Test transformation with mid_price field"""
        response = {
            "data": [
                {"symbol": "BTC", "mid_price": "50000.00"},
                {"symbol": "ETH", "mid_price": "3000.00"}
            ]
        }

        result = AccountTransformer.transform_all_mids(response)

        assert result["BTC"] == "50000.00"
        assert result["ETH"] == "3000.00"

    def test_with_bid_ask(self):
        """Test transformation calculating mid from bid/ask"""
        response = {
            "data": [
                {"symbol": "BTC", "bid": "49990.00", "ask": "50010.00"}
            ]
        }

        result = AccountTransformer.transform_all_mids(response)

        assert result["BTC"] == "50000.0"

    def test_with_price_fallback(self):
        """Test transformation with price field as fallback"""
        response = {
            "data": [
                {"symbol": "BTC", "price": "50000.00"}
            ]
        }

        result = AccountTransformer.transform_all_mids(response)

        assert result["BTC"] == "50000.00"

    def test_empty_data(self):
        """Test empty data list"""
        response = {"data": []}

        result = AccountTransformer.transform_all_mids(response)

        assert result == {}


class TestTransformMeta:
    """Tests for AccountTransformer.transform_meta()"""

    def test_basic_transformation(self, sample_markets_response):
        """Test basic meta transformation"""
        result = AccountTransformer.transform_meta(sample_markets_response)

        assert "universe" in result
        assert len(result["universe"]) == 2

    def test_market_fields(self, sample_markets_response):
        """Test market fields are present"""
        result = AccountTransformer.transform_meta(sample_markets_response)

        market = result["universe"][0]
        assert "name" in market
        assert "szDecimals" in market
        assert "maxLeverage" in market
        assert "onlyIsolated" in market

    def test_market_values(self, sample_markets_response):
        """Test market values are correctly mapped"""
        result = AccountTransformer.transform_meta(sample_markets_response)

        btc = result["universe"][0]
        assert btc["name"] == "BTC"
        assert btc["szDecimals"] == 6
        assert btc["maxLeverage"] == 100
        assert btc["onlyIsolated"] is False

    def test_isolated_only_market(self, sample_markets_response):
        """Test isolated-only market flag"""
        result = AccountTransformer.transform_meta(sample_markets_response)

        eth = result["universe"][1]
        assert eth["onlyIsolated"] is True


class TestTransformL2Book:
    """Tests for AccountTransformer.transform_l2_book()"""

    def test_basic_transformation(self):
        """Test basic L2 book transformation"""
        response = {
            "data": {
                "symbol": "BTC",
                "bids": [
                    {"price": "49990.00", "size": "1.5"},
                    {"price": "49980.00", "size": "2.0"}
                ],
                "asks": [
                    {"price": "50010.00", "size": "1.2"},
                    {"price": "50020.00", "size": "2.5"}
                ],
                "timestamp": 1700000000000
            }
        }

        result = AccountTransformer.transform_l2_book(response)

        assert result["coin"] == "BTC"
        assert result["time"] == 1700000000000
        assert "levels" in result

    def test_bid_levels(self):
        """Test bid levels transformation"""
        response = {
            "data": {
                "symbol": "BTC",
                "bids": [
                    {"price": "49990.00", "size": "1.5"}
                ],
                "asks": [],
                "timestamp": 1700000000000
            }
        }

        result = AccountTransformer.transform_l2_book(response)

        bid_levels = result["levels"][0][0]
        assert len(bid_levels) == 1
        assert bid_levels[0]["px"] == "49990.00"
        assert bid_levels[0]["sz"] == "1.5"
        assert bid_levels[0]["n"] == 1

    def test_ask_levels(self):
        """Test ask levels transformation"""
        response = {
            "data": {
                "symbol": "ETH",
                "bids": [],
                "asks": [
                    {"price": "3010.00", "size": "5.0"}
                ],
                "timestamp": 1700000000000
            }
        }

        result = AccountTransformer.transform_l2_book(response)

        ask_levels = result["levels"][0][1]
        assert len(ask_levels) == 1
        assert ask_levels[0]["px"] == "3010.00"
        assert ask_levels[0]["sz"] == "5.0"


class TestTransformUserRateLimit:
    """Tests for AccountTransformer.transform_user_rate_limit()"""

    def test_basic_transformation(self, sample_rate_limit_response):
        """Test basic rate limit transformation"""
        result = AccountTransformer.transform_user_rate_limit(
            sample_rate_limit_response
        )

        assert result["nRequestsUsed"] == 150
        assert result["nRequestsCap"] == 1000
        assert result["resetTime"] == 1700003600000

    def test_default_values(self):
        """Test default values when fields are missing"""
        response = {"data": {}}

        result = AccountTransformer.transform_user_rate_limit(response)

        assert result["nRequestsUsed"] == 0
        assert result["nRequestsCap"] == 1000
        assert result["resetTime"] == 0
