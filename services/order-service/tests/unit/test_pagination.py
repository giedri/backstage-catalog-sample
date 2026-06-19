"""Tests for the HMAC-signed pagination token utility."""

import base64
import json

import pytest

from src.utils.pagination import (
    InvalidPaginationTokenError,
    decode_pagination_token,
    encode_pagination_token,
)

SECRET = "test-secret-key-for-pagination"
SAMPLE_KEY = {
    "pk": "ORDER#ORD-001",
    "sk": "ORDER#ORD-001",
    "gsi1pk": "CUSTOMER#CUST-001",
    "gsi1sk": "2024-01-15T10:30:00+00:00",
}


class TestEncodePaginationToken:
    def test_produces_valid_base64_string(self):
        token = encode_pagination_token(SAMPLE_KEY, "CUST-001", SECRET)

        # Should be a non-empty string
        assert isinstance(token, str)
        assert len(token) > 0

        # Should be valid base64url
        decoded = base64.urlsafe_b64decode(token)
        data = json.loads(decoded)
        assert "payload" in data
        assert "customer_id" in data
        assert "signature" in data

    def test_raises_error_with_empty_secret(self):
        """Encoding with an empty secret must raise InvalidPaginationTokenError."""
        with pytest.raises(InvalidPaginationTokenError):
            encode_pagination_token(SAMPLE_KEY, "CUST-001", "")


class TestDecodePaginationToken:
    def test_round_trip(self):
        token = encode_pagination_token(SAMPLE_KEY, "CUST-001", SECRET)
        result = decode_pagination_token(token, "CUST-001", SECRET)

        assert result == SAMPLE_KEY

    def test_rejects_cross_customer_token(self):
        """A token for CUST-001 must be rejected when decoded with CUST-002."""
        token = encode_pagination_token(SAMPLE_KEY, "CUST-001", SECRET)

        with pytest.raises(InvalidPaginationTokenError):
            decode_pagination_token(token, "CUST-002", SECRET)

    def test_rejects_tampered_payload(self):
        """A token with modified payload bytes is rejected."""
        token = encode_pagination_token(SAMPLE_KEY, "CUST-001", SECRET)

        # Decode the outer token, tamper with payload, re-encode
        token_json = base64.urlsafe_b64decode(token)
        token_data = json.loads(token_json)

        # Modify the payload (change a character)
        original_payload = token_data["payload"]
        payload_bytes = bytearray(base64.b64decode(original_payload))
        payload_bytes[0] ^= 0xFF  # flip bits in first byte
        token_data["payload"] = base64.b64encode(bytes(payload_bytes)).decode()

        tampered_token = base64.urlsafe_b64encode(
            json.dumps(token_data).encode()
        ).decode()

        with pytest.raises(InvalidPaginationTokenError):
            decode_pagination_token(tampered_token, "CUST-001", SECRET)

    def test_rejects_forged_signature(self):
        """A token with a forged signature is rejected."""
        token = encode_pagination_token(SAMPLE_KEY, "CUST-001", SECRET)

        # Decode the outer token, replace signature, re-encode
        token_json = base64.urlsafe_b64decode(token)
        token_data = json.loads(token_json)
        token_data["signature"] = "a" * 64  # forged hex string

        forged_token = base64.urlsafe_b64encode(
            json.dumps(token_data).encode()
        ).decode()

        with pytest.raises(InvalidPaginationTokenError):
            decode_pagination_token(forged_token, "CUST-001", SECRET)

    def test_rejects_invalid_base64(self):
        """A completely invalid base64 string is rejected."""
        with pytest.raises(InvalidPaginationTokenError):
            decode_pagination_token("!!!not-valid-base64!!!", "CUST-001", SECRET)

    def test_rejects_empty_string(self):
        """An empty string is rejected."""
        with pytest.raises(InvalidPaginationTokenError):
            decode_pagination_token("", "CUST-001", SECRET)

    def test_rejects_old_style_plain_base64_token(self):
        """A plain base64 token (no signature structure) is rejected."""
        # This is what the old code produced: plain base64 of JSON key
        old_token = base64.b64encode(json.dumps(SAMPLE_KEY).encode()).decode()

        with pytest.raises(InvalidPaginationTokenError):
            decode_pagination_token(old_token, "CUST-001", SECRET)

    def test_raises_error_with_empty_secret(self):
        """Decoding with an empty secret must raise InvalidPaginationTokenError."""
        token = encode_pagination_token(SAMPLE_KEY, "CUST-001", SECRET)

        with pytest.raises(InvalidPaginationTokenError):
            decode_pagination_token(token, "CUST-001", "")
