"""
Shared pytest fixtures for Pacifica SDK tests
"""

import pytest


# =============================================================================
# Account/Position Fixtures
# =============================================================================

@pytest.fixture
def sample_account_response():
    """Sample Pacifica account API response"""
    return {
        "data": {
            "account_equity": "10000.50",
            "balance": "8500.00",
            "available_to_withdraw": "5000.00",
            "total_margin_used": "3500.50",
            "cross_mmr": "1200.25"
        }
    }


@pytest.fixture
def sample_positions_response():
    """Sample Pacifica positions API response"""
    return {
        "data": [
            {
                "symbol": "BTC",
                "side": "bid",
                "amount": "0.5",
                "entry_price": "50000.00",
                "leverage": 10,
                "isolated": False,
                "margin": "2500.00",
                "liquidation_price": "45000.00",
                "unrealized_pnl": "250.00",
                "roe": "0.10",
                "max_trade_size": "5.0"
            },
            {
                "symbol": "ETH",
                "side": "ask",
                "amount": "2.0",
                "entry_price": "3000.00",
                "leverage": 5,
                "isolated": True,
                "margin": "1200.00",
                "liquidation_price": "3500.00",
                "unrealized_pnl": "-50.00",
                "roe": "-0.04",
                "max_trade_size": "20.0"
            }
        ]
    }


@pytest.fixture
def empty_positions_response():
    """Empty positions response"""
    return {"data": []}


@pytest.fixture
def empty_account_response():
    """Empty/new account response"""
    return {
        "data": {
            "account_equity": "0",
            "balance": "0",
            "available_to_withdraw": "0",
            "total_margin_used": "0",
            "cross_mmr": "0"
        }
    }


# =============================================================================
# Order Fixtures
# =============================================================================

@pytest.fixture
def sample_orders_response():
    """Sample Pacifica open orders API response"""
    return {
        "data": [
            {
                "symbol": "BTC",
                "order_id": 12345,
                "side": "bid",
                "initial_price": "48000.00",
                "amount": "0.5",
                "remaining_amount": "0.3",
                "created_at": 1700000000000,
                "client_order_id": "client-order-1"
            },
            {
                "symbol": "ETH",
                "order_id": 12346,
                "side": "ask",
                "initial_price": "3100.00",
                "amount": "1.0",
                "remaining_amount": "1.0",
                "created_at": 1700000001000,
                "client_order_id": None
            }
        ]
    }


@pytest.fixture
def empty_orders_response():
    """Empty orders response"""
    return {"data": []}


# =============================================================================
# Trade/Fill Fixtures
# =============================================================================

@pytest.fixture
def sample_trades_response():
    """Sample Pacifica trades/fills API response"""
    return {
        "data": [
            {
                "symbol": "BTC",
                "order_id": 12345,
                "price": "49000.00",
                "amount": "0.2",
                "side": "long_open",
                "created_at": 1700000000000,
                "start_position": "0.0",
                "pnl": "0",
                "tx_hash": "0xabc123",
                "event_type": "fulfill_taker",
                "fee": "9.80",
                "history_id": 99001,
                "is_liquidation": False,
                "client_order_id": "client-order-1"
            },
            {
                "symbol": "ETH",
                "order_id": 12350,
                "price": "3050.00",
                "amount": "1.5",
                "side": "short_close",
                "created_at": 1700000002000,
                "start_position": "-2.0",
                "pnl": "75.00",
                "tx_hash": "0xdef456",
                "event_type": "fulfill_maker",
                "fee": "4.58",
                "history_id": 99002,
                "is_liquidation": False,
                "client_order_id": None
            }
        ]
    }


@pytest.fixture
def sample_liquidation_trade():
    """Sample liquidation trade"""
    return {
        "data": [
            {
                "symbol": "SOL",
                "order_id": 12399,
                "price": "100.00",
                "amount": "10.0",
                "side": "long_close",
                "created_at": 1700000005000,
                "start_position": "10.0",
                "pnl": "-500.00",
                "tx_hash": "0xliq789",
                "event_type": "fulfill_taker",
                "fee": "0",
                "history_id": 99010,
                "is_liquidation": True,
                "client_order_id": None
            }
        ]
    }


# =============================================================================
# Funding Fixtures
# =============================================================================

@pytest.fixture
def sample_funding_response():
    """Sample Pacifica funding history API response"""
    return {
        "data": [
            {
                "symbol": "BTC",
                "funding_rate": "0.0001",
                "position_size": "0.5",
                "timestamp": 1700000000000,
                "tx_hash": "0xfund123",
                "funding_amount": "2.50"
            },
            {
                "symbol": "ETH",
                "funding_rate": "-0.0002",
                "position_size": "-2.0",
                "timestamp": 1700003600000,
                "tx_hash": "0xfund456",
                "funding_amount": "-1.20"
            }
        ]
    }


# =============================================================================
# Balance/Ledger Fixtures
# =============================================================================

@pytest.fixture
def sample_balance_events():
    """Sample Pacifica balance history events"""
    return [
        {
            "amount": "1000.00",
            "balance": "1000.00",
            "event_type": "deposit",
            "created_at": 1699900000000,
            "tx_hash": "0xdep001"
        },
        {
            "amount": "500.00",
            "balance": "500.00",
            "event_type": "withdraw",
            "created_at": 1699950000000,
            "tx_hash": "0xwith001"
        },
        {
            "amount": "200.00",
            "balance": "700.00",
            "event_type": "subaccount_transfer",
            "created_at": 1699960000000,
            "tx_hash": "0xtrans001"
        },
        {
            "amount": "50.00",
            "balance": "750.00",
            "event_type": "deposit_release",
            "created_at": 1699970000000,
            "tx_hash": "0xrel001"
        },
        {
            "amount": "10.00",
            "balance": "740.00",
            "event_type": "fee",
            "created_at": 1699980000000,
            "tx_hash": "0xfee001"
        }
    ]


# =============================================================================
# Market Data Fixtures
# =============================================================================

@pytest.fixture
def sample_markets_response():
    """Sample Pacifica markets/meta API response"""
    return {
        "data": [
            {
                "symbol": "BTC",
                "size_decimals": 6,
                "max_leverage": 100,
                "isolated_only": False,
                "lot_size": "0.0001",
                "tick_size": "0.1",
                "min_tick": "0",
                "max_tick": "1000000",
                "min_order_size": "10",
                "max_order_size": "10000000",
                "funding_rate": "0.0001",
                "next_funding_rate": "0.00012",
                "created_at": 1690000000000
            },
            {
                "symbol": "ETH",
                "size_decimals": 5,
                "max_leverage": 50,
                "isolated_only": True,
                "lot_size": "0.001",
                "tick_size": "0.01",
                "min_tick": "0",
                "max_tick": "100000",
                "min_order_size": "10",
                "max_order_size": "5000000",
                "funding_rate": "-0.0002",
                "next_funding_rate": "-0.00015",
                "created_at": 1690000000000
            }
        ]
    }


@pytest.fixture
def sample_prices_response():
    """Sample Pacifica prices API response"""
    return {
        "data": [
            {"symbol": "BTC", "mid": "50000.50"},
            {"symbol": "ETH", "mid": "3000.25"},
            {"symbol": "SOL", "mid": "100.10"}
        ]
    }


@pytest.fixture
def sample_orderbook_response():
    """Sample Pacifica orderbook API response"""
    return {
        "data": {
            "symbol": "BTC",
            "bids": [
                ["49990.00", "1.5"],
                ["49980.00", "2.0"],
                ["49970.00", "3.5"]
            ],
            "asks": [
                ["50010.00", "1.2"],
                ["50020.00", "2.5"],
                ["50030.00", "4.0"]
            ],
            "timestamp": 1700000000000
        }
    }


@pytest.fixture
def sample_candles_response():
    """Sample Pacifica candles API response"""
    return {
        "data": [
            {
                "timestamp": 1700000000000,
                "open": "49000.00",
                "high": "50500.00",
                "low": "48500.00",
                "close": "50000.00",
                "volume": "1234.56",
                "trades_count": 5000
            },
            {
                "timestamp": 1700003600000,
                "open": "50000.00",
                "high": "51000.00",
                "low": "49500.00",
                "close": "50500.00",
                "volume": "987.65",
                "trades_count": 4500
            }
        ]
    }


@pytest.fixture
def sample_funding_rates_response():
    """Sample Pacifica funding rates API response"""
    return {
        "data": [
            {
                "symbol": "BTC",
                "funding_rate": "0.0001",
                "premium": "0.00005",
                "next_funding_time": 1700007200000
            },
            {
                "symbol": "ETH",
                "funding_rate": "-0.0002",
                "premium": "-0.0001",
                "next_funding_time": 1700007200000
            }
        ]
    }


@pytest.fixture
def sample_open_interest_response():
    """Sample Pacifica open interest API response"""
    return {
        "data": [
            {
                "symbol": "BTC",
                "open_interest": "15000.5",
                "open_interest_value": "750000000"
            },
            {
                "symbol": "ETH",
                "open_interest": "250000.0",
                "open_interest_value": "750000000"
            }
        ]
    }


# =============================================================================
# Rate Limit Fixtures
# =============================================================================

@pytest.fixture
def sample_rate_limit_response():
    """Sample rate limit API response"""
    return {
        "data": {
            "requests_used": 150,
            "requests_cap": 1000,
            "reset_time": 1700003600000
        }
    }
