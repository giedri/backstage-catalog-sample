"""Unit tests for src.utils.auth module (Cognito-based auth)."""

import pytest

from src.utils.auth import (
    AuthError,
    get_user_claims,
    get_user_id,
    is_admin,
    require_admin,
    require_owner_or_admin,
)


def _make_event(claims: dict) -> dict:
    """Build a minimal event with JWT authorizer claims."""
    return {
        "requestContext": {
            "authorizer": {
                "jwt": {
                    "claims": claims,
                }
            }
        }
    }


class TestGetUserClaims:
    def test_valid_claims(self):
        event = _make_event({"sub": "USER-001", "email": "user@example.com", "cognito:groups": "admin editors"})
        claims = get_user_claims(event)
        assert claims["sub"] == "USER-001"
        assert claims["email"] == "user@example.com"
        assert claims["groups"] == ["admin", "editors"]

    def test_missing_authorizer_raises_unauthorized(self):
        event = {"requestContext": {"http": {"method": "GET"}}}
        with pytest.raises(AuthError) as exc_info:
            get_user_claims(event)
        assert exc_info.value.code == "UNAUTHORIZED"

    def test_missing_sub_raises_unauthorized(self):
        event = _make_event({"email": "user@example.com", "cognito:groups": ""})
        with pytest.raises(AuthError) as exc_info:
            get_user_claims(event)
        assert exc_info.value.code == "UNAUTHORIZED"

    def test_empty_sub_raises_unauthorized(self):
        event = _make_event({"sub": "", "cognito:groups": ""})
        with pytest.raises(AuthError) as exc_info:
            get_user_claims(event)
        assert exc_info.value.code == "UNAUTHORIZED"

    def test_groups_from_space_separated_string(self):
        event = _make_event({"sub": "USER-001", "cognito:groups": "admin editors viewers"})
        claims = get_user_claims(event)
        assert claims["groups"] == ["admin", "editors", "viewers"]

    def test_groups_from_list(self):
        event = _make_event({"sub": "USER-001", "cognito:groups": ["admin", "editors"]})
        claims = get_user_claims(event)
        assert claims["groups"] == ["admin", "editors"]

    def test_empty_groups_string(self):
        event = _make_event({"sub": "USER-001", "cognito:groups": ""})
        claims = get_user_claims(event)
        assert claims["groups"] == []

    def test_no_groups_claim(self):
        event = _make_event({"sub": "USER-001"})
        claims = get_user_claims(event)
        assert claims["groups"] == []


class TestGetUserId:
    def test_returns_sub(self):
        event = _make_event({"sub": "USER-001", "cognito:groups": ""})
        assert get_user_id(event) == "USER-001"

    def test_missing_auth_raises(self):
        event = {"requestContext": {}}
        with pytest.raises(AuthError):
            get_user_id(event)


class TestIsAdmin:
    def test_admin_in_groups(self):
        event = _make_event({"sub": "USER-001", "cognito:groups": "admin"})
        assert is_admin(event) is True

    def test_not_admin(self):
        event = _make_event({"sub": "USER-001", "cognito:groups": "editors"})
        assert is_admin(event) is False

    def test_no_groups(self):
        event = _make_event({"sub": "USER-001", "cognito:groups": ""})
        assert is_admin(event) is False


class TestRequireAdmin:
    def test_admin_passes(self):
        event = _make_event({"sub": "ADMIN-001", "cognito:groups": "admin"})
        claims = require_admin(event)
        assert claims["sub"] == "ADMIN-001"

    def test_non_admin_raises_forbidden(self):
        event = _make_event({"sub": "USER-001", "cognito:groups": ""})
        with pytest.raises(AuthError) as exc_info:
            require_admin(event)
        assert exc_info.value.code == "FORBIDDEN"


class TestRequireOwnerOrAdmin:
    def test_owner_passes(self):
        event = _make_event({"sub": "USER-001", "cognito:groups": ""})
        claims = require_owner_or_admin(event, "USER-001")
        assert claims["sub"] == "USER-001"

    def test_admin_passes_for_different_owner(self):
        event = _make_event({"sub": "ADMIN-001", "cognito:groups": "admin"})
        claims = require_owner_or_admin(event, "USER-002")
        assert claims["sub"] == "ADMIN-001"

    def test_non_owner_non_admin_raises_forbidden(self):
        event = _make_event({"sub": "USER-001", "cognito:groups": ""})
        with pytest.raises(AuthError) as exc_info:
            require_owner_or_admin(event, "USER-002")
        assert exc_info.value.code == "FORBIDDEN"
