class EmailNotVerifiedError(Exception):
    """Raised when user tries to login with unverified email"""

    pass


class InvalidCredentials(Exception):
    """Raised when email or password is incorrect"""

    pass


class InvalidTokenError(Exception):
    """Raised when token is invalid or malformed"""

    pass


class TokenExpiredError(Exception):
    """Raised when token has expired"""

    pass


class Unauthorized(Exception):
    """Raised when user is not authorized"""

    pass
