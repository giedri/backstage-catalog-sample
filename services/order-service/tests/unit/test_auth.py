"""Unit tests for the auth utility module."""

from src.utils.auth import authorize_customer_access, get_customer_id_from_event
from tests.conftest import make_api_event


class TestGetCustomerIdFromEvent:
    def test_valid_claims(self):
        event = make_api_event(claims={"customer_id": "CUST-001"})
        result = get_customer_id_from_event(event)
        assert result == "CUST-001"

    def test_missing_authorizer_context(self):
        event = make_api_event()
        result = get_customer_id_from_event(event)
        assert result is None

    def test_missing_jwt_key(self):
        event = make_api_event()
        event["requestContext"]["authorizer"] = {}
        result = get_customer_id_from_event(event)
        assert result is None

    def test_missing_claims_key(self):
        event = make_api_event()
        event["requestContext"]["authorizer"] = {"jwt": {}}
        result = get_customer_id_from_event(event)
        assert result is None

    def test_empty_customer_id_claim(self):
        event = make_api_event(claims={"customer_id": ""})
        result = get_customer_id_from_event(event)
        assert result is None

    def test_missing_customer_id_claim(self):
        event = make_api_event(claims={"sub": "user-123"})
        result = get_customer_id_from_event(event)
        assert result is None

    def test_none_request_context(self):
        event = {"requestContext": None}
        result = get_customer_id_from_event(event)
        assert result is None

    def test_non_string_customer_id_integer(self):
        event = make_api_event(claims={"customer_id": 12345})
        result = get_customer_id_from_event(event)
        assert result is None

    def test_non_string_customer_id_list(self):
        event = make_api_event(claims={"customer_id": ["CUST-001"]})
        result = get_customer_id_from_event(event)
        assert result is None

    def test_non_string_customer_id_dict(self):
        event = make_api_event(claims={"customer_id": {"id": "CUST-001"}})
        result = get_customer_id_from_event(event)
        assert result is None


class TestAuthorizeCustomerAccess:
    def test_matching_customer_id(self):
        event = make_api_event(claims={"customer_id": "CUST-001"})
        is_authorized, authenticated_id = authorize_customer_access(event, "CUST-001")
        assert is_authorized is True
        assert authenticated_id == "CUST-001"

    def test_mismatched_customer_id(self):
        event = make_api_event(claims={"customer_id": "CUST-001"})
        is_authorized, authenticated_id = authorize_customer_access(event, "CUST-002")
        assert is_authorized is False
        assert authenticated_id == "CUST-001"

    def test_missing_claims(self):
        event = make_api_event()
        is_authorized, authenticated_id = authorize_customer_access(event, "CUST-001")
        assert is_authorized is False
        assert authenticated_id is None

    def test_empty_customer_id_in_claims(self):
        event = make_api_event(claims={"customer_id": ""})
        is_authorized, authenticated_id = authorize_customer_access(event, "CUST-001")
        assert is_authorized is False
        assert authenticated_id is None
