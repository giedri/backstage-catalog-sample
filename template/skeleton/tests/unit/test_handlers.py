import json

import pytest
from moto import mock_aws

from tests.conftest import _NO_AUTH, make_api_event


@mock_aws
class TestCreateItemHandler:
    def test_create_item_success(self, dynamodb_table):
        from src.handlers.create_item import lambda_handler

        event = make_api_event(
            method="POST",
            path="/v1/items",
            body={"name": "Test Item", "description": "A test", "owner_id": "OWNER-001"},
        )
        response = lambda_handler(event, None)

        assert response["statusCode"] == 201
        body = json.loads(response["body"])
        assert body["name"] == "Test Item"
        assert body["owner_id"] == "OWNER-001"

    def test_create_item_missing_fields(self, dynamodb_table):
        from src.handlers.create_item import lambda_handler

        event = make_api_event(method="POST", path="/v1/items", body={})
        response = lambda_handler(event, None)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["error"]["code"] == "BAD_REQUEST"

    def test_create_item_forbidden_different_owner(self, dynamodb_table):
        from src.handlers.create_item import lambda_handler

        event = make_api_event(
            method="POST",
            path="/v1/items",
            body={"name": "Test Item", "description": "A test", "owner_id": "OWNER-999"},
            claims={"sub": "OWNER-001"},
        )
        response = lambda_handler(event, None)

        assert response["statusCode"] == 403
        body = json.loads(response["body"])
        assert body["error"]["code"] == "FORBIDDEN"

    def test_create_item_unauthorized_no_auth(self, dynamodb_table):
        from src.handlers.create_item import lambda_handler

        event = make_api_event(
            method="POST",
            path="/v1/items",
            body={"name": "Test Item", "description": "A test", "owner_id": "OWNER-001"},
            claims=_NO_AUTH,
        )
        response = lambda_handler(event, None)

        assert response["statusCode"] == 401
        body = json.loads(response["body"])
        assert body["error"]["code"] == "UNAUTHORIZED"


@mock_aws
class TestGetItemHandler:
    def test_get_item_not_found(self, dynamodb_table):
        from src.handlers.get_item import lambda_handler

        event = make_api_event(
            method="GET",
            path="/v1/items/nonexistent",
            path_parameters={"itemId": "nonexistent"},
        )
        response = lambda_handler(event, None)

        assert response["statusCode"] == 404

    def test_get_item_forbidden_different_owner(self, dynamodb_table, item_service):
        from src.handlers.get_item import lambda_handler

        item = item_service.create_item(
            name="Secret Item", description="Private", owner_id="OWNER-002"
        )

        event = make_api_event(
            method="GET",
            path=f"/v1/items/{item.item_id}",
            path_parameters={"itemId": item.item_id},
            claims={"sub": "OWNER-001"},
        )
        response = lambda_handler(event, None)

        assert response["statusCode"] == 404
        body = json.loads(response["body"])
        assert body["error"]["code"] == "NOT_FOUND"

    def test_get_item_unauthorized_no_auth(self, dynamodb_table):
        from src.handlers.get_item import lambda_handler

        event = make_api_event(
            method="GET",
            path="/v1/items/some-id",
            path_parameters={"itemId": "some-id"},
            claims=_NO_AUTH,
        )
        response = lambda_handler(event, None)

        assert response["statusCode"] == 401


@mock_aws
class TestListItemsHandler:
    def test_list_items_success(self, dynamodb_table, item_service):
        from src.handlers.list_items import lambda_handler

        item_service.create_item(name="Item 1", description="Desc", owner_id="OWNER-001")

        event = make_api_event(
            method="GET",
            path="/v1/items",
            claims={"sub": "OWNER-001"},
        )
        response = lambda_handler(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert len(body["items"]) == 1

    def test_list_items_unauthorized_no_auth(self, dynamodb_table):
        from src.handlers.list_items import lambda_handler

        event = make_api_event(
            method="GET",
            path="/v1/items",
            claims=_NO_AUTH,
        )
        response = lambda_handler(event, None)

        assert response["statusCode"] == 401


@mock_aws
class TestDeleteItemHandler:
    def test_delete_item_not_found(self, dynamodb_table):
        from src.handlers.delete_item import lambda_handler

        event = make_api_event(
            method="DELETE",
            path="/v1/items/nonexistent",
            path_parameters={"itemId": "nonexistent"},
        )
        response = lambda_handler(event, None)

        assert response["statusCode"] == 404

    def test_delete_item_forbidden_different_owner(self, dynamodb_table, item_service):
        from src.handlers.delete_item import lambda_handler

        item = item_service.create_item(
            name="Secret Item", description="Private", owner_id="OWNER-002"
        )

        event = make_api_event(
            method="DELETE",
            path=f"/v1/items/{item.item_id}",
            path_parameters={"itemId": item.item_id},
            claims={"sub": "OWNER-001"},
        )
        response = lambda_handler(event, None)

        assert response["statusCode"] == 404
        body = json.loads(response["body"])
        assert body["error"]["code"] == "NOT_FOUND"

    def test_delete_item_unauthorized_no_auth(self, dynamodb_table):
        from src.handlers.delete_item import lambda_handler

        event = make_api_event(
            method="DELETE",
            path="/v1/items/some-id",
            path_parameters={"itemId": "some-id"},
            claims=_NO_AUTH,
        )
        response = lambda_handler(event, None)

        assert response["statusCode"] == 401


@mock_aws
class TestHealthHandler:
    def test_health(self):
        from src.handlers.health import lambda_handler

        response = lambda_handler({}, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["status"] == "healthy"
