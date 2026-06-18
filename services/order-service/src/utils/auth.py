"""Authentication and authorization utilities.

Extracts user identity and group membership from the API Gateway request context
populated by the Cognito JWT authorizer.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class AuthError(Exception):
    """Raised when authentication or authorization fails."""

    def __init__(self, message: str, code: str = "FORBIDDEN"):
        super().__init__(message)
        self.code = code
        self.message = message


def get_user_claims(event: dict) -> dict:
    """Extract user claims from the API Gateway JWT authorizer context.

    When using HTTP API (v2) with a JWT authorizer, the decoded JWT claims are
    available in event['requestContext']['authorizer']['jwt']['claims'].

    Returns:
        dict with keys: sub, email, groups
    """
    try:
        jwt_context = event["requestContext"]["authorizer"]["jwt"]["claims"]
    except (KeyError, TypeError):
        logger.error("Missing JWT authorizer context in event")
        raise AuthError("Missing authentication context", code="UNAUTHORIZED")

    sub = jwt_context.get("sub")
    if not sub:
        logger.error("Missing 'sub' claim in JWT token")
        raise AuthError("Invalid token: missing subject", code="UNAUTHORIZED")

    # Cognito groups come as a space-separated string in the 'cognito:groups' claim
    groups_raw = jwt_context.get("cognito:groups", "")
    if isinstance(groups_raw, list):
        groups = groups_raw
    elif isinstance(groups_raw, str) and groups_raw:
        groups = [g.strip() for g in groups_raw.split(" ") if g.strip()]
    else:
        groups = []

    return {
        "sub": sub,
        "email": jwt_context.get("email", ""),
        "groups": groups,
    }


def get_user_id(event: dict) -> str:
    """Get the authenticated user's unique identifier (sub claim).

    Returns:
        The Cognito user sub (UUID).
    """
    claims = get_user_claims(event)
    return claims["sub"]


def is_admin(event: dict) -> bool:
    """Check if the authenticated user belongs to the 'admin' group.

    Returns:
        True if user is in the admin group.
    """
    claims = get_user_claims(event)
    return "admin" in claims["groups"]


def require_admin(event: dict) -> dict:
    """Verify the user is an admin. Raises AuthError if not.

    Returns:
        The user claims dict.
    """
    claims = get_user_claims(event)
    if "admin" not in claims["groups"]:
        logger.warning(
            "User %s attempted admin action without admin group membership",
            claims["sub"],
        )
        raise AuthError("Admin privileges required", code="FORBIDDEN")
    return claims


def require_owner_or_admin(event: dict, resource_owner_id: str) -> dict:
    """Verify the user owns the resource or is an admin.

    Args:
        event: The Lambda event with JWT authorizer context.
        resource_owner_id: The owner (customer_id) of the resource being accessed.

    Returns:
        The user claims dict.

    Raises:
        AuthError: If the user is neither the owner nor an admin.
    """
    claims = get_user_claims(event)
    user_id = claims["sub"]

    if user_id != resource_owner_id and "admin" not in claims["groups"]:
        logger.warning(
            "User %s denied access to resource owned by %s",
            user_id,
            resource_owner_id,
        )
        raise AuthError("Access denied: you do not own this resource", code="FORBIDDEN")

    return claims
