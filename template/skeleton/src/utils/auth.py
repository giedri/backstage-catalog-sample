"""JWT authentication and authorization utilities."""

from __future__ import annotations


class UnauthorizedError(Exception):
    """Raised when a request lacks valid authentication or authorization."""

    pass


def get_caller_identity(event: dict) -> str:
    """Extract the authenticated owner_id from JWT claims.

    The API Gateway HTTP API v2 JWT authorizer places verified claims
    at event.requestContext.authorizer.jwt.claims.  The 'sub' claim
    represents the owner_id.

    Raises:
        UnauthorizedError: If the authorizer context or sub claim is missing.
    """
    try:
        claims = event["requestContext"]["authorizer"]["jwt"]["claims"]
        owner_id = claims["sub"]
        if not owner_id:
            raise UnauthorizedError("Missing subject claim in token")
        return owner_id
    except (KeyError, TypeError):
        raise UnauthorizedError("Missing or invalid authorization context")
