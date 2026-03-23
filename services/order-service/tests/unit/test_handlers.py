import json

import pytest
from moto import mock_aws

from tests.conftest import make_api_event


SAMPLE_ITEMS = [
    {
        "product_id": "PROD-001",
        "product_name": "Widget",
        "quantity": 2,
        "unit_price": 9.99,
    },
]


@mock_aws
class TestCreateOrderHandler:
    def test_create_order_success(self, dynamodb_table):
        from src.handlers.create_order import lambda_handler

        event = make_api_event(
            method="POST",
            path="/v1/orders",
            body={"customer_id": "CUST-001", "items": SAMPLE_ITEMS},
        )
        response = lambda_handler(event, None)

        assert response["statusCode"] == 201
        body = json.loads(response["body"])
        assert body["customer_id"] == "CUST-001"
        assert body["status"] == "PENDING"

    def test_create_order_missing_fields(self, dynamodb_table):
        from src.handlers.create_order import lambda_handler

        event = make_api_event(method="POST", path="/v1/orders", body={})
        response = lambda_handler(event, None)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["error"]["code"] == "BAD_REQUEST"


@mock_aws
class TestGetOrderHandler:
    def test_get_order_not_found(self, dynamodb_table):
        from src.handlers.get_order import lambda_handler

        event = make_api_event(
            method="GET",
            path="/v1/orders/nonexistent",
            path_parameters={"orderId": "nonexistent"},
        )
        response = lambda_handler(event, None)

        assert response["statusCode"] == 404


@mock_aws
class TestListOrdersHandler:
    def test_list_orders_missing_customer(self, dynamodb_table):
        from src.handlers.list_orders import lambda_handler

        event = make_api_event(method="GET", path="/v1/orders")
        response = lambda_handler(event, None)

        assert response["statusCode"] == 400


@mock_aws
class TestHealthHandler:
    def test_health(self):
        from src.handlers.health import lambda_handler

        response = lambda_handler({}, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["status"] == "healthy"
