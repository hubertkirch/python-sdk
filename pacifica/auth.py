"""
Solana-based authentication for Pacifica API
"""

import base58
from typing import Dict, Optional, Any
from solders.keypair import Keypair
from solders.message import Message
from solders.signature import Signature
from solders.pubkey import Pubkey
import json


class PacificaAuth:
    """
    Authentication handler for Pacifica API using Solana keypairs.
    Compatible with Hyperliquid SDK interface.
    """

    def __init__(self, private_key: str, main_account: Optional[str] = None, skip_onboarding: bool = False):
        """
        Initialize authentication with a Solana private key.

        Args:
            private_key: Base58-encoded Solana private key (main account or agent key)
            main_account: If provided, private_key is treated as agent key
            skip_onboarding: Not used (for Hyperliquid compatibility)
        """
        self.keypair = Keypair.from_base58_string(private_key)
        self.public_key = str(self.keypair.pubkey())
        self.main_account = main_account  # If set, we're in agent mode
        self.skip_onboarding = skip_onboarding

    def sign_request(self, message: str) -> str:
        """
        Sign a message with the Solana keypair.

        Args:
            message: Message to sign

        Returns:
            Base58-encoded signature
        """
        msg_bytes = message.encode('utf-8')
        signature = self.keypair.sign_message(msg_bytes)
        return base58.b58encode(bytes(signature)).decode('utf-8')

    def get_auth_headers(self, message: Optional[str] = None) -> Dict[str, str]:
        """
        Get authentication headers for API requests.

        Args:
            message: Optional message to sign

        Returns:
            Dictionary of auth headers
        """
        headers = {
            "X-Account": self.public_key
        }

        if message:
            signature = self.sign_request(message)
            headers["X-Signature"] = signature
            headers["X-Message"] = message

        return headers

    def sign_message(self, header: Dict, payload: Dict) -> tuple:
        """
        Sign a message with header and payload.
        Compatible with Pacifica's batch order signing.

        Args:
            header: Signature header with type, timestamp, expiry_window
            payload: The data to sign

        Returns:
            Tuple of (message, signature)
        """
        # Validate header
        if not all(key in header for key in ["type", "timestamp", "expiry_window"]):
            raise ValueError("Header must have type, timestamp, and expiry_window")

        # Prepare the message
        data = {
            **header,
            "data": payload,
        }

        # Sort keys and create compact JSON
        sorted_data = self._sort_json_keys(data)
        message = json.dumps(sorted_data, separators=(",", ":"))

        # Sign the message
        message_bytes = message.encode("utf-8")
        signature = self.keypair.sign_message(message_bytes)
        signature_b58 = base58.b58encode(bytes(signature)).decode("ascii")

        return (message, signature_b58)

    def _sort_json_keys(self, value: Any) -> Any:
        """Recursively sort JSON keys for consistent signing"""
        if isinstance(value, dict):
            return {key: self._sort_json_keys(value[key]) for key in sorted(value.keys())}
        elif isinstance(value, list):
            return [self._sort_json_keys(item) for item in value]
        return value

    def get_public_key(self) -> str:
        """
        Get the public key (Solana address).

        Returns:
            Public key as string
        """
        return self.public_key

    def is_agent_mode(self) -> bool:
        """
        Check if we're operating in agent mode.

        Returns:
            True if main_account is set (agent mode), False otherwise
        """
        return self.main_account is not None

    def get_account(self) -> str:
        """
        Get the account address for API requests.

        Returns:
            Main account address if in agent mode, otherwise own public key
        """
        return self.main_account if self.main_account else self.public_key

    def get_agent_wallet(self) -> Optional[str]:
        """
        Get the agent wallet address if in agent mode.

        Returns:
            Agent wallet address (own public key) if in agent mode, None otherwise
        """
        return self.public_key if self.main_account else None

    def is_mainnet(self) -> bool:
        """
        Check if using mainnet (always true for Pacifica).
        For Hyperliquid compatibility.

        Returns:
            True
        """
        return True