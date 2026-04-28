"""
Exceções customizadas para autenticação.
"""


class AuthError(Exception):
    def __init__(self, message: str = "Authentication failed", code: str = "AUTH_ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)


class MissingCredentialsError(AuthError):
    def __init__(self, message: str = "No authentication credentials provided"):
        super().__init__(message, code="MISSING_CREDENTIALS")


class InvalidTokenError(AuthError):
    def __init__(self, message: str = "Invalid authentication token"):
        super().__init__(message, code="INVALID_TOKEN")


class TokenExpiredError(AuthError):
    def __init__(self, message: str = "Authentication token has expired"):
        super().__init__(message, code="TOKEN_EXPIRED")


class InvalidSignatureError(InvalidTokenError):
    def __init__(self, message: str = "Token signature verification failed"):
        super().__init__(message)
        self.code = "INVALID_SIGNATURE"


class InvalidApiKeyError(AuthError):
    def __init__(self, message: str = "Invalid API key"):
        super().__init__(message, code="INVALID_API_KEY")


class ClientNotFoundError(AuthError):
    def __init__(self, message: str = "Client not found for provided credentials"):
        super().__init__(message, code="CLIENT_NOT_FOUND")


class AuthDisabledError(AuthError):
    def __init__(self, message: str = "Authentication is disabled"):
        super().__init__(message, code="AUTH_DISABLED")
