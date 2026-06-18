"""Authorization utilities for extracting and validating JWT claims.

IMPORTANT: This module expects the identity provider (IdP) to include a custom
"customer_id" claim in the JWT. This is NOT a standard OIDC claim. The IdP must
be configured to map the internal customer identifier to this claim name.

For example, in AWS Cognito this requires a pre-token-generation Lambda trigger
or a custom attribute (custom:customer_id) mapped to the "customer_id" claim.
Without this claim, all requests will be denied (fail-closed behavior).
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def get_customer_id_from_event(event: dict) -> str | None:
    """Extract the customer_id claim from the JWT authorizer context.

    For HTTP API v2 with a JWT authorizer, claims are located at:
    event['requestContext']['authorizer']['jwt']['claims']['customer_id']

    Returns the customer_id string if present, or None if claims are
    missing or malformed.
    """
    try:
        claims = event["requestContext"]["authorizer"]["jwt"]["claims"]
        customer_id = claims.get("customer_id")
        if not customer_id:
            logger.warning("customer_id claim is missing or empty")
            return None
        if not isinstance(customer_id, str):
            logger.warning("customer_id claim is not a string: %s", type(customer_id).__name__)
            return None
        return customer_id
    except (KeyError, TypeError) as e:
        logger.warning("Failed to extract customer_id from JWT claims: %s", e)
        return None


def authorize_customer_access(
    event: dict, requested_customer_id: str
) -> tuple[bool, str | None]:
    """Validate that the authenticated user matches the requested customer_id.

    Returns a tuple of (is_authorized, authenticated_customer_id).
    - If authorized: (True, authenticated_customer_id)
    - If not authorized (mismatch): (False, authenticated_customer_id)
    - If claims are missing: (False, None)
    """
    authenticated_customer_id = get_customer_id_from_event(event)

    if authenticated_customer_id is None:
        return False, None

    if authenticated_customer_id != requested_customer_id:
        logger.warning(
            "Authorization denied: token customer_id=%s, requested=%s",
            authenticated_customer_id,
            requested_customer_id,
        )
        return False, authenticated_customer_id

    return True, authenticated_customer_id
