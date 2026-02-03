"""
Pacifica Python SDK - Hyperliquid-compatible interface for Pacifica DEX
"""

from pacifica.client import Client
from pacifica.setup import setup
from pacifica.auth import PacificaAuth
from pacifica.async_client import AsyncPacificaClient

__version__ = "0.2.0"
__all__ = ["Client", "setup", "PacificaAuth", "AsyncPacificaClient"]