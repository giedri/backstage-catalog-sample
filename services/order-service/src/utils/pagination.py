"""HMAC-signed pagination token utilities.

Tokens bind the DynamoDB LastEvaluatedKey to a specific customer_id using
HMAC-SHA256 so that tokens cannot be forged or replayed across customers.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging

logger = logging.getLogger(__name__)


class InvalidPaginationTokenError(ValueError):
    """Raised when a pagination token fails validation.

    Carries a generic user-facing message while logging the actual reason.
    """

    def __init__(self, reason: str = ""):
        self._reason = reason
        if reason:
            logger.warning("Invalid pagination token: %s", reason)
        super().__init__("Invalid pagination token")


def _compute_signature(payload_b64: str, customer_id: str, secret: str) -> str:
    """Compute HMAC-SHA256 over payload_b64 + '.' + customer_id."""
    message = f"{payload_b64}.{customer_id}"
    return hmac.new(
        secret.encode(),
        message.encode(),
        hashlib.sha256,
    ).hexdigest()


def encode_pagination_token(
    last_evaluated_key: dict, customer_id: str, secret: str
) -> str:
    """Encode a DynamoDB LastEvaluatedKey into a signed pagination token.

    The token is a base64url-encoded JSON object containing:
    - payload: base64-encoded JSON of the DynamoDB key
    - customer_id: the customer this token is bound to
    - signature: HMAC-SHA256 hex digest
    """
    payload_bytes = json.dumps(last_evaluated_key).encode()
    payload_b64 = base64.b64encode(payload_bytes).decode()

    signature = _compute_signature(payload_b64, customer_id, secret)

    token_data = {
        "payload": payload_b64,
        "customer_id": customer_id,
        "signature": signature,
    }
    token_json = json.dumps(token_data).encode()
    return base64.urlsafe_b64encode(token_json).decode()


def decode_pagination_token(token: str, customer_id: str, secret: str) -> dict:
    """Decode and verify a signed pagination token.

    Raises InvalidPaginationTokenError if verification fails.
    Returns the deserialized DynamoDB ExclusiveStartKey dict on success.
    """
    if not token:
        raise InvalidPaginationTokenError("empty token")

    try:
        token_json = base64.urlsafe_b64decode(token)
        token_data = json.loads(token_json)
    except Exception:
        raise InvalidPaginationTokenError("malformed token encoding")

    if not isinstance(token_data, dict):
        raise InvalidPaginationTokenError("token is not a JSON object")

    required_keys = {"payload", "customer_id", "signature"}
    if not required_keys.issubset(token_data.keys()):
        raise InvalidPaginationTokenError("missing required token fields")

    # Verify customer_id binding
    if token_data["customer_id"] != customer_id:
        raise InvalidPaginationTokenError("customer_id mismatch")

    # Recompute signature and verify with timing-safe comparison
    payload_b64 = token_data["payload"]
    expected_signature = _compute_signature(payload_b64, customer_id, secret)

    if not hmac.compare_digest(expected_signature, token_data["signature"]):
        raise InvalidPaginationTokenError("signature verification failed")

    # Decode the payload
    try:
        payload_bytes = base64.b64decode(payload_b64)
        return json.loads(payload_bytes)
    except Exception:
        raise InvalidPaginationTokenError("payload decode failed")
