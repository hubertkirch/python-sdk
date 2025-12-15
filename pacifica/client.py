"""
Pacifica Client - Hyperliquid-compatible interface

This module provides the main Client class that matches Hyperliquid's structure exactly.
"""

from typing import Optional
from .api.info import InfoAPI
from .api.exchange import ExchangeAPI
from .auth import PacificaAuth


class Client:
    """
    Main Pacifica client with Hyperliquid-compatible structure.

    Usage:
        from pacifica.client import Client

        client = Client(private_key='your_solana_key')

        # Access sub-clients
        user_state = client.info.user_state(address)
        order_result = client.exchange.order('BTC', True, 0.01, 50000)
    """

    def __init__(
        self,
        private_key: Optional[str] = None,
        main_account: Optional[str] = None,
        base_url: Optional[str] = None,
        testnet: bool = False,
        timeout: int = 30,
        skip_onboarding: bool = False
    ):
        """
        Initialize Pacifica Client.

        Args:
            private_key: Solana private key (base58 encoded) - main account or agent key
            main_account: If provided, private_key is treated as agent key
            base_url: Override API base URL
            testnet: Use testnet instead of mainnet
            timeout: Request timeout in seconds
            skip_onboarding: Not used (for Hyperliquid compatibility)
        """
        # Initialize authentication
        self.auth = PacificaAuth(private_key, main_account, skip_onboarding) if private_key else None
        self.main_account = main_account

        # Store configuration
        self.timeout = timeout
        self.testnet = testnet
        self.base_url = base_url or (InfoAPI.TESTNET_API if testnet else InfoAPI.MAINNET_API)

        # Initialize sub-clients as properties (like Hyperliquid)
        self.info = InfoAPI(
            auth=self.auth,
            base_url=base_url,
            testnet=testnet,
            timeout=timeout
        )

        self.exchange = ExchangeAPI(
            auth=self.auth,
            base_url=base_url,
            testnet=testnet,
            timeout=timeout
        )

    @property
    def public_key(self) -> Optional[str]:
        """Get the public key/address from auth."""
        if self.auth:
            return self.auth.get_public_key()
        return None

    @property
    def address(self) -> Optional[str]:
        """Get the address - returns main account if in agent mode, otherwise own key."""
        if self.auth:
            return self.auth.get_account()
        return None

