class EmailNotVerifiedError(Exception):
    """Raised when user tries to login with unverified email"""


class InvalidCredentials(Exception):
    """Raised when email or password is incorrect"""


class InvalidTokenError(Exception):
    """Raised when token is invalid or malformed"""


class TokenExpiredError(Exception):
    """Raised when token has expired"""


class Unauthorized(Exception):
    """Raised when user is not authorized"""
