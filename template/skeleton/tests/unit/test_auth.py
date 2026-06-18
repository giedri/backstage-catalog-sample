"""Unit tests for src.utils.auth module."""

import pytest

from src.utils.auth import UnauthorizedError, get_caller_identity


class TestGetCallerIdentity:
    def test_valid_claims(self):
        event = {
            "requestContext": {
                "authorizer": {
                    "jwt": {
                        "claims": {"sub": "OWNER-001"}
                    }
                }
            }
        }
        assert get_caller_identity(event) == "OWNER-001"

    def test_missing_authorizer_raises(self):
        event = {"requestContext": {"http": {"method": "GET"}}}
        with pytest.raises(UnauthorizedError):
            get_caller_identity(event)

    def test_missing_jwt_key_raises(self):
        event = {"requestContext": {"authorizer": {}}}
        with pytest.raises(UnauthorizedError):
            get_caller_identity(event)

    def test_missing_sub_claim_raises(self):
        event = {
            "requestContext": {
                "authorizer": {
                    "jwt": {
                        "claims": {}
                    }
                }
            }
        }
        with pytest.raises(UnauthorizedError):
            get_caller_identity(event)

    def test_empty_sub_claim_raises(self):
        event = {
            "requestContext": {
                "authorizer": {
                    "jwt": {
                        "claims": {"sub": ""}
                    }
                }
            }
        }
        with pytest.raises(UnauthorizedError):
            get_caller_identity(event)

    def test_none_request_context_raises(self):
        event = {}
        with pytest.raises(UnauthorizedError):
            get_caller_identity(event)
