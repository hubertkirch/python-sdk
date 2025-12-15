"""
Exception classes for Pacifica SDK
"""


class PacificaError(Exception):
    """Base exception for Pacifica SDK"""
    pass


class PacificaAPIError(PacificaError):
    """API request error"""

    def __init__(self, status_code: int, message: str, response: dict = None):
        self.status_code = status_code
        self.message = message
        self.response = response
        super().__init__(f"API Error {status_code}: {message}")


class PacificaAuthError(PacificaError):
    """Authentication error"""
    pass


class PacificaAccountNotFoundError(PacificaError):
    """Account not found (no trading history)"""

    def __init__(self, account: str):
        self.account = account
        super().__init__(f"Account {account} not found (no trading history)")


class PacificaBetaAccessError(PacificaError):
    """Beta access required error"""

    def __init__(self, message: str = "Beta access required for trading"):
        super().__init__(message)