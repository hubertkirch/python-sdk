"""
Setup utility function for Pacifica SDK - Hyperliquid compatible

This module provides the setup function that initializes the SDK components
exactly like Hyperliquid's setup function.
"""

from typing import Tuple, Optional
from .client import Client
from .api.info import InfoAPI
from .api.exchange import ExchangeAPI


def setup(
    private_key: str,
    main_account: Optional[str] = None,
    base_url: Optional[str] = None,
    testnet: bool = False,
    skip_ws: bool = True
) -> Tuple[str, InfoAPI, ExchangeAPI]:
    """
    Initialize Pacifica SDK - Hyperliquid compatible interface.

    This function matches Hyperliquid's setup function exactly, returning
    a tuple of (address, info, exchange).

    Args:
        private_key: Solana private key (base58 string) - main account or agent key
        main_account: If provided, private_key is treated as agent key
        base_url: Optional API base URL override
        testnet: Use testnet instead of mainnet
        skip_ws: Skip WebSocket connections (REST only) - for compatibility

    Returns:
        Tuple of (address, info, exchange) - identical to Hyperliquid

    Example:
        from pacifica.setup import setup

        # Direct account trading (no agent key)
        address, info, exchange = setup(
            private_key="your_main_account_private_key",
            testnet=True
        )

        # Agent key trading
        address, info, exchange = setup(
            private_key="your_agent_key_private_key",
            main_account="your_main_account_address",
            testnet=True
        )

        # Use the components
        user_state = info.user_state(address)
        order_result = exchange.order("BTC", True, 0.01, 50000)
    """
    # Create the client
    client = Client(
        private_key=private_key,
        main_account=main_account,
        base_url=base_url,
        testnet=testnet,
        skip_onboarding=not skip_ws  # Map skip_ws to skip_onboarding for compatibility
    )

    # Extract the address from the client - will be main account if in agent mode
    address = client.address
    if not address:
        raise ValueError("Failed to derive address from private key")

    # Return the tuple exactly like Hyperliquid
    return address, client.info, client.exchange