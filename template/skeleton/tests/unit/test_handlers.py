import json

import pytest
from moto import mock_aws

from tests.conftest import make_api_event


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


@mock_aws
class TestListItemsHandler:
    def test_list_items_missing_owner(self, dynamodb_table):
        from src.handlers.list_items import lambda_handler

        event = make_api_event(method="GET", path="/v1/items")
        response = lambda_handler(event, None)

        assert response["statusCode"] == 400


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


@mock_aws
class TestHealthHandler:
    def test_health(self):
        from src.handlers.health import lambda_handler

        response = lambda_handler({}, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["status"] == "healthy"
