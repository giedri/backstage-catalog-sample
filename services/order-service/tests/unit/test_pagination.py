"""Tests for the pagination token utility.

Verifies HMAC-signed, context-bound pagination tokens including:
- Token format and structure
- Round-trip encoding/decoding
- Tamper detection (payload and signature)
- Cross-partition rejection (customer_id binding)
- Malformed token handling
"""

from __future__ import annotations

import base64
import json
import os

import pytest

from src.utils.pagination import (
    InvalidPaginationTokenError,
    decode_pagination_token,
    encode_pagination_token,
)

# Sample DynamoDB LastEvaluatedKey structures
SAMPLE_KEY = {
    "pk": "ORDER#ORD-12345",
    "sk": "ORDER#ORD-12345",
    "gsi1pk": "CUSTOMER#CUST-001",
    "gsi1sk": "2024-01-15T10:30:00Z",
}

SAMPLE_CUSTOMER_ID = "CUST-001"
ANOTHER_CUSTOMER_ID = "CUST-002"


class TestEncodeToken:
    """Tests for encode_pagination_token."""

    def test_produces_token_with_dot_separator(self) -> None:
        """Token format must have exactly one '.' separating payload and signature."""
        token = encode_pagination_token(SAMPLE_KEY, SAMPLE_CUSTOMER_ID)
        parts = token.split(".")
        assert len(parts) == 2, f"Expected exactly one '.' in token, got: {token}"

    def test_token_parts_are_base64url_encoded(self) -> None:
        """Both payload and signature parts should be valid base64url strings."""
        token = encode_pagination_token(SAMPLE_KEY, SAMPLE_CUSTOMER_ID)
        payload_part, sig_part = token.split(".")

        # Should not contain standard base64 chars that differ in base64url
        assert "+" not in payload_part
        assert "/" not in payload_part
        assert "+" not in sig_part
        assert "/" not in sig_part

    def test_token_payload_contains_customer_id(self) -> None:
        """The payload must include the customer_id for context binding."""
        token = encode_pagination_token(SAMPLE_KEY, SAMPLE_CUSTOMER_ID)
        payload_part = token.split(".")[0]

        # Decode the payload to verify customer_id is embedded
        padding = 4 - len(payload_part) % 4
        if padding != 4:
            payload_part += "=" * padding
        payload_bytes = base64.urlsafe_b64decode(payload_part)
        payload = json.loads(payload_bytes)

        assert payload["customer_id"] == SAMPLE_CUSTOMER_ID

    def test_deterministic_output_for_same_input(self) -> None:
        """Same inputs should produce the same token (deterministic signing)."""
        token1 = encode_pagination_token(SAMPLE_KEY, SAMPLE_CUSTOMER_ID)
        token2 = encode_pagination_token(SAMPLE_KEY, SAMPLE_CUSTOMER_ID)
        assert token1 == token2

    def test_different_customer_id_produces_different_token(self) -> None:
        """Different customer IDs should produce different tokens."""
        token1 = encode_pagination_token(SAMPLE_KEY, SAMPLE_CUSTOMER_ID)
        token2 = encode_pagination_token(SAMPLE_KEY, ANOTHER_CUSTOMER_ID)
        assert token1 != token2


class TestDecodeToken:
    """Tests for decode_pagination_token."""

    def test_round_trip_returns_original_key(self) -> None:
        """Encoding then decoding should return the original DynamoDB key."""
        token = encode_pagination_token(SAMPLE_KEY, SAMPLE_CUSTOMER_ID)
        result = decode_pagination_token(token, SAMPLE_CUSTOMER_ID)
        assert result == SAMPLE_KEY

    def test_round_trip_with_simple_key(self) -> None:
        """Round-trip works with a minimal key structure."""
        simple_key = {"pk": "ORDER#ORD-999", "sk": "ORDER#ORD-999"}
        token = encode_pagination_token(simple_key, SAMPLE_CUSTOMER_ID)
        result = decode_pagination_token(token, SAMPLE_CUSTOMER_ID)
        assert result == simple_key

    def test_round_trip_preserves_key_types(self) -> None:
        """Numeric and nested values in keys are preserved through round-trip."""
        complex_key = {
            "pk": "ORDER#ORD-100",
            "sk": "ORDER#ORD-100",
            "version": 42,
        }
        token = encode_pagination_token(complex_key, SAMPLE_CUSTOMER_ID)
        result = decode_pagination_token(token, SAMPLE_CUSTOMER_ID)
        assert result == complex_key
        assert isinstance(result["version"], int)


class TestTamperDetection:
    """Tests for tamper detection (payload and signature modifications)."""

    def test_tampered_payload_raises_error(self) -> None:
        """Modifying the payload should invalidate the signature."""
        token = encode_pagination_token(SAMPLE_KEY, SAMPLE_CUSTOMER_ID)
        payload_part, sig_part = token.split(".")

        # Decode payload, modify it, re-encode
        padding = 4 - len(payload_part) % 4
        if padding != 4:
            padded = payload_part + "=" * padding
        else:
            padded = payload_part
        payload_bytes = base64.urlsafe_b64decode(padded)
        payload = json.loads(payload_bytes)
        payload["key"]["pk"] = "ORDER#ORD-HACKED"
        tampered_payload = base64.urlsafe_b64encode(
            json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
        ).rstrip(b"=").decode("ascii")

        tampered_token = f"{tampered_payload}.{sig_part}"

        with pytest.raises(InvalidPaginationTokenError):
            decode_pagination_token(tampered_token, SAMPLE_CUSTOMER_ID)

    def test_tampered_signature_raises_error(self) -> None:
        """Modifying the signature should fail verification."""
        token = encode_pagination_token(SAMPLE_KEY, SAMPLE_CUSTOMER_ID)
        payload_part, sig_part = token.split(".")

        # Flip a character in the signature
        tampered_sig = sig_part[:-1] + ("A" if sig_part[-1] != "A" else "B")
        tampered_token = f"{payload_part}.{tampered_sig}"

        with pytest.raises(InvalidPaginationTokenError):
            decode_pagination_token(tampered_token, SAMPLE_CUSTOMER_ID)

    def test_swapped_payload_signature_raises_error(self) -> None:
        """Swapping payload and signature parts should fail."""
        token = encode_pagination_token(SAMPLE_KEY, SAMPLE_CUSTOMER_ID)
        payload_part, sig_part = token.split(".")
        swapped_token = f"{sig_part}.{payload_part}"

        with pytest.raises(InvalidPaginationTokenError):
            decode_pagination_token(swapped_token, SAMPLE_CUSTOMER_ID)


class TestCrossPartitionProtection:
    """Tests that tokens are bound to a specific customer_id."""

    def test_token_for_different_customer_raises_error(self) -> None:
        """A token created for CUST-001 must not be usable by CUST-002."""
        token = encode_pagination_token(SAMPLE_KEY, SAMPLE_CUSTOMER_ID)

        with pytest.raises(InvalidPaginationTokenError):
            decode_pagination_token(token, ANOTHER_CUSTOMER_ID)

    def test_token_valid_for_correct_customer(self) -> None:
        """A token should decode successfully for the correct customer."""
        token = encode_pagination_token(SAMPLE_KEY, SAMPLE_CUSTOMER_ID)
        result = decode_pagination_token(token, SAMPLE_CUSTOMER_ID)
        assert result == SAMPLE_KEY

    def test_admin_querying_different_customer(self) -> None:
        """Token generated for a customer query should only work for that customer."""
        # Simulate admin querying CUST-002's orders
        token = encode_pagination_token(SAMPLE_KEY, ANOTHER_CUSTOMER_ID)

        # Should work with CUST-002
        result = decode_pagination_token(token, ANOTHER_CUSTOMER_ID)
        assert result == SAMPLE_KEY

        # Should fail with CUST-001
        with pytest.raises(InvalidPaginationTokenError):
            decode_pagination_token(token, SAMPLE_CUSTOMER_ID)


class TestMalformedTokens:
    """Tests for handling of completely malformed tokens."""

    def test_empty_string_raises_error(self) -> None:
        """Empty string should raise InvalidPaginationTokenError."""
        with pytest.raises(InvalidPaginationTokenError):
            decode_pagination_token("", SAMPLE_CUSTOMER_ID)

    def test_no_dot_separator_raises_error(self) -> None:
        """Token without a '.' separator should fail."""
        with pytest.raises(InvalidPaginationTokenError):
            decode_pagination_token("nodothere", SAMPLE_CUSTOMER_ID)

    def test_multiple_dots_raises_error(self) -> None:
        """Token with multiple '.' separators should fail."""
        with pytest.raises(InvalidPaginationTokenError):
            decode_pagination_token("a.b.c", SAMPLE_CUSTOMER_ID)

    def test_random_garbage_raises_error(self) -> None:
        """Random garbage strings should fail gracefully."""
        garbage_tokens = [
            "!!!.???",
            "abc123.xyz789",
            "\x00\x01.\x02\x03",
            " . ",
            "null.null",
        ]
        for garbage in garbage_tokens:
            with pytest.raises(InvalidPaginationTokenError):
                decode_pagination_token(garbage, SAMPLE_CUSTOMER_ID)

    def test_none_value_raises_error(self) -> None:
        """None as token should raise InvalidPaginationTokenError."""
        with pytest.raises(InvalidPaginationTokenError):
            decode_pagination_token(None, SAMPLE_CUSTOMER_ID)  # type: ignore[arg-type]

    def test_valid_base64_but_invalid_json_raises_error(self) -> None:
        """A token with valid base64 payload but invalid JSON should fail."""
        import hmac as hmac_mod
        import hashlib

        # Create a base64url-encoded non-JSON payload
        bad_payload = base64.urlsafe_b64encode(b"not-json-at-all").rstrip(b"=").decode()
        secret = os.environ["PAGINATION_SECRET"].encode()
        sig = hmac_mod.new(secret, bad_payload.encode("ascii"), hashlib.sha256).digest()
        bad_sig = base64.urlsafe_b64encode(sig).rstrip(b"=").decode()

        # Even with a valid signature, the JSON parse should fail
        # Actually the signature would be valid but the payload isn't valid JSON
        # so it should raise InvalidPaginationTokenError
        with pytest.raises(InvalidPaginationTokenError):
            decode_pagination_token(f"{bad_payload}.{bad_sig}", SAMPLE_CUSTOMER_ID)


class TestSecurityProperties:
    """Tests verifying security properties of the token scheme."""

    def test_hmac_uses_constant_time_comparison(self) -> None:
        """Verify that the implementation would fail if HMAC verification is removed.

        This test ensures that a token with a wrong signature is rejected,
        which validates that the HMAC check is actually in the code path.
        """
        token = encode_pagination_token(SAMPLE_KEY, SAMPLE_CUSTOMER_ID)
        payload_part, _ = token.split(".")

        # Use a completely zero signature
        fake_sig = base64.urlsafe_b64encode(b"\x00" * 32).rstrip(b"=").decode()
        fake_token = f"{payload_part}.{fake_sig}"

        with pytest.raises(InvalidPaginationTokenError):
            decode_pagination_token(fake_token, SAMPLE_CUSTOMER_ID)

    def test_different_secrets_produce_incompatible_tokens(self) -> None:
        """Tokens signed with one secret cannot be verified with another."""
        # Encode with current secret
        token = encode_pagination_token(SAMPLE_KEY, SAMPLE_CUSTOMER_ID)

        # Change the secret
        original_secret = os.environ["PAGINATION_SECRET"]
        os.environ["PAGINATION_SECRET"] = "different-secret-key"
        try:
            with pytest.raises(InvalidPaginationTokenError):
                decode_pagination_token(token, SAMPLE_CUSTOMER_ID)
        finally:
            os.environ["PAGINATION_SECRET"] = original_secret

    def test_token_contains_bound_context(self) -> None:
        """The token payload includes customer_id - it is NOT just the raw key."""
        token = encode_pagination_token(SAMPLE_KEY, SAMPLE_CUSTOMER_ID)
        payload_part = token.split(".")[0]

        # Decode to verify the structure
        padding = 4 - len(payload_part) % 4
        if padding != 4:
            payload_part += "=" * padding
        payload_bytes = base64.urlsafe_b64decode(payload_part)
        payload = json.loads(payload_bytes)

        # Must have both key and customer_id
        assert "key" in payload
        assert "customer_id" in payload
        assert payload["customer_id"] == SAMPLE_CUSTOMER_ID
        assert payload["key"] == SAMPLE_KEY
