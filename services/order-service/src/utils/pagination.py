"""Secure pagination token utilities.

Encodes and decodes HMAC-signed, context-bound pagination tokens to prevent
token forgery, cross-partition access, and exposure of internal DynamoDB key schema.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os

logger = logging.getLogger(__name__)


class InvalidPaginationTokenError(ValueError):
    """Raised when a pagination token fails validation."""

    def __init__(self, message: str = "Invalid pagination token"):
        super().__init__(message)


def _get_secret() -> bytes:
    """Retrieve the HMAC signing secret from environment."""
    secret = os.environ.get("PAGINATION_SECRET")
    if not secret:
        raise RuntimeError("PAGINATION_SECRET environment variable is not set")
    return secret.encode("utf-8")


def _base64url_encode(data: bytes) -> str:
    """Base64url-encode bytes without padding."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _base64url_decode(s: str) -> bytes:
    """Base64url-decode a string, adding back padding as needed."""
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)


def encode_pagination_token(last_evaluated_key: dict, customer_id: str) -> str:
    """Encode a DynamoDB LastEvaluatedKey into a signed pagination token.

    The token binds the key to the customer_id so it cannot be reused
    across different customer queries.

    Args:
        last_evaluated_key: The DynamoDB LastEvaluatedKey dict.
        customer_id: The customer ID to bind the token to.

    Returns:
        A signed token string in the format: base64url(payload).base64url(signature)
    """
    payload = {
        "key": last_evaluated_key,
        "customer_id": customer_id,
    }
    payload_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    encoded_payload = _base64url_encode(payload_bytes)

    secret = _get_secret()
    signature = hmac.new(secret, encoded_payload.encode("ascii"), hashlib.sha256).digest()
    encoded_signature = _base64url_encode(signature)

    return f"{encoded_payload}.{encoded_signature}"


def decode_pagination_token(token: str, customer_id: str) -> dict:
    """Decode and verify a signed pagination token.

    Validates the HMAC signature and checks that the customer_id in the token
    matches the provided customer_id.

    Args:
        token: The pagination token string.
        customer_id: The expected customer ID (must match the one in the token).

    Returns:
        The DynamoDB LastEvaluatedKey dict.

    Raises:
        InvalidPaginationTokenError: If the token is malformed, has an invalid
            signature, or the customer_id does not match.
    """
    if not token or not isinstance(token, str):
        raise InvalidPaginationTokenError()

    parts = token.split(".")
    if len(parts) != 2:
        raise InvalidPaginationTokenError()

    encoded_payload, encoded_signature = parts

    # Verify signature
    try:
        secret = _get_secret()
        expected_signature = hmac.new(
            secret, encoded_payload.encode("ascii"), hashlib.sha256
        ).digest()
        provided_signature = _base64url_decode(encoded_signature)
    except Exception:
        raise InvalidPaginationTokenError()

    if not hmac.compare_digest(expected_signature, provided_signature):
        raise InvalidPaginationTokenError()

    # Decode and validate payload
    try:
        payload_bytes = _base64url_decode(encoded_payload)
        payload = json.loads(payload_bytes)
    except Exception:
        raise InvalidPaginationTokenError()

    if not isinstance(payload, dict):
        raise InvalidPaginationTokenError()

    token_customer_id = payload.get("customer_id")
    if token_customer_id != customer_id:
        raise InvalidPaginationTokenError()

    key = payload.get("key")
    if not isinstance(key, dict):
        raise InvalidPaginationTokenError()

    return key
