import json

import pytest
from moto import mock_aws

from tests.conftest import _NO_AUTH, make_api_event


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
            body={"items": SAMPLE_ITEMS},
            claims={"sub": "CUST-001", "cognito:groups": ""},
        )
        response = lambda_handler(event, None)

        assert response["statusCode"] == 201
        body = json.loads(response["body"])
        assert body["customer_id"] == "CUST-001"
        assert body["status"] == "PENDING"

    def test_create_order_missing_items(self, dynamodb_table):
        from src.handlers.create_order import lambda_handler

        event = make_api_event(
            method="POST",
            path="/v1/orders",
            body={},
            claims={"sub": "CUST-001", "cognito:groups": ""},
        )
        response = lambda_handler(event, None)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["error"]["code"] == "BAD_REQUEST"

    def test_create_order_unauthorized(self, dynamodb_table):
        from src.handlers.create_order import lambda_handler

        event = make_api_event(
            method="POST",
            path="/v1/orders",
            body={"items": SAMPLE_ITEMS},
            claims=_NO_AUTH,
        )
        response = lambda_handler(event, None)

        assert response["statusCode"] == 401
        body = json.loads(response["body"])
        assert body["error"]["code"] == "UNAUTHORIZED"


@mock_aws
class TestGetOrderHandler:
    def test_get_order_not_found(self, dynamodb_table):
        from src.handlers.get_order import lambda_handler

        event = make_api_event(
            method="GET",
            path="/v1/orders/nonexistent",
            path_parameters={"orderId": "nonexistent"},
            claims={"sub": "CUST-001", "cognito:groups": ""},
        )
        response = lambda_handler(event, None)

        assert response["statusCode"] == 404

    def test_get_order_success_as_owner(self, dynamodb_table, order_service):
        from src.handlers.get_order import lambda_handler

        order = order_service.create_order(
            customer_id="CUST-001", items=SAMPLE_ITEMS
        )

        event = make_api_event(
            method="GET",
            path=f"/v1/orders/{order.order_id}",
            path_parameters={"orderId": order.order_id},
            claims={"sub": "CUST-001", "cognito:groups": ""},
        )
        response = lambda_handler(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["order_id"] == order.order_id
        assert body["customer_id"] == "CUST-001"

    def test_get_order_returns_404_for_non_owner(self, dynamodb_table, order_service):
        """Non-admin user accessing another user's order gets 404 (not 403)."""
        from src.handlers.get_order import lambda_handler

        order = order_service.create_order(
            customer_id="CUST-002", items=SAMPLE_ITEMS
        )

        event = make_api_event(
            method="GET",
            path=f"/v1/orders/{order.order_id}",
            path_parameters={"orderId": order.order_id},
            claims={"sub": "CUST-001", "cognito:groups": ""},
        )
        response = lambda_handler(event, None)

        assert response["statusCode"] == 404
        body = json.loads(response["body"])
        assert body["error"]["code"] == "NOT_FOUND"

    def test_get_order_admin_can_access_any_order(self, dynamodb_table, order_service):
        """Admin users can access any order regardless of ownership."""
        from src.handlers.get_order import lambda_handler

        order = order_service.create_order(
            customer_id="CUST-002", items=SAMPLE_ITEMS
        )

        event = make_api_event(
            method="GET",
            path=f"/v1/orders/{order.order_id}",
            path_parameters={"orderId": order.order_id},
            claims={"sub": "ADMIN-001", "cognito:groups": "admin"},
        )
        response = lambda_handler(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["order_id"] == order.order_id

    def test_get_order_unauthorized(self, dynamodb_table):
        from src.handlers.get_order import lambda_handler

        event = make_api_event(
            method="GET",
            path="/v1/orders/some-id",
            path_parameters={"orderId": "some-id"},
            claims=_NO_AUTH,
        )
        response = lambda_handler(event, None)

        assert response["statusCode"] == 401
        body = json.loads(response["body"])
        assert body["error"]["code"] == "UNAUTHORIZED"


@mock_aws
class TestListOrdersHandler:
    def test_list_orders_success(self, dynamodb_table, order_service):
        from src.handlers.list_orders import lambda_handler

        order_service.create_order(customer_id="CUST-001", items=SAMPLE_ITEMS)

        event = make_api_event(
            method="GET",
            path="/v1/orders",
            claims={"sub": "CUST-001", "cognito:groups": ""},
        )
        response = lambda_handler(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert len(body["items"]) == 1
        assert body["items"][0]["customer_id"] == "CUST-001"

    def test_list_orders_admin_can_query_other_customer(
        self, dynamodb_table, order_service
    ):
        """Admin can pass customer_id query param to see another user's orders."""
        from src.handlers.list_orders import lambda_handler

        order_service.create_order(customer_id="CUST-002", items=SAMPLE_ITEMS)

        event = make_api_event(
            method="GET",
            path="/v1/orders",
            query_string_parameters={"customer_id": "CUST-002"},
            claims={"sub": "ADMIN-001", "cognito:groups": "admin"},
        )
        response = lambda_handler(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert len(body["items"]) == 1
        assert body["items"][0]["customer_id"] == "CUST-002"

    def test_list_orders_non_admin_customer_id_ignored(
        self, dynamodb_table, order_service
    ):
        """Non-admin user's customer_id query param is ignored; gets own orders."""
        from src.handlers.list_orders import lambda_handler

        order_service.create_order(customer_id="CUST-001", items=SAMPLE_ITEMS)
        order_service.create_order(customer_id="CUST-002", items=SAMPLE_ITEMS)

        event = make_api_event(
            method="GET",
            path="/v1/orders",
            query_string_parameters={"customer_id": "CUST-002"},
            claims={"sub": "CUST-001", "cognito:groups": ""},
        )
        response = lambda_handler(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        # Should only see own orders, not CUST-002's
        for order in body["items"]:
            assert order["customer_id"] == "CUST-001"

    def test_list_orders_unauthorized(self, dynamodb_table):
        from src.handlers.list_orders import lambda_handler

        event = make_api_event(
            method="GET",
            path="/v1/orders",
            claims=_NO_AUTH,
        )
        response = lambda_handler(event, None)

        assert response["statusCode"] == 401
        body = json.loads(response["body"])
        assert body["error"]["code"] == "UNAUTHORIZED"


@mock_aws
class TestUpdateOrderStatusHandler:
    def test_update_order_status_success_as_admin(
        self, dynamodb_table, order_service
    ):
        from src.handlers.update_order_status import lambda_handler

        order = order_service.create_order(
            customer_id="CUST-001", items=SAMPLE_ITEMS
        )

        event = make_api_event(
            method="PATCH",
            path=f"/v1/orders/{order.order_id}/status",
            path_parameters={"orderId": order.order_id},
            body={"status": "CONFIRMED"},
            claims={"sub": "ADMIN-001", "cognito:groups": "admin"},
        )
        response = lambda_handler(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["status"] == "CONFIRMED"

    def test_update_order_status_forbidden_non_admin(self, dynamodb_table):
        from src.handlers.update_order_status import lambda_handler

        event = make_api_event(
            method="PATCH",
            path="/v1/orders/some-id/status",
            path_parameters={"orderId": "some-id"},
            body={"status": "CONFIRMED"},
            claims={"sub": "CUST-001", "cognito:groups": ""},
        )
        response = lambda_handler(event, None)

        assert response["statusCode"] == 403
        body = json.loads(response["body"])
        assert body["error"]["code"] == "FORBIDDEN"

    def test_update_order_status_unauthorized(self, dynamodb_table):
        from src.handlers.update_order_status import lambda_handler

        event = make_api_event(
            method="PATCH",
            path="/v1/orders/some-id/status",
            path_parameters={"orderId": "some-id"},
            body={"status": "CONFIRMED"},
            claims=_NO_AUTH,
        )
        response = lambda_handler(event, None)

        assert response["statusCode"] == 401
        body = json.loads(response["body"])
        assert body["error"]["code"] == "UNAUTHORIZED"

    def test_update_order_status_invalid_transition(
        self, dynamodb_table, order_service
    ):
        from src.handlers.update_order_status import lambda_handler

        order = order_service.create_order(
            customer_id="CUST-001", items=SAMPLE_ITEMS
        )

        event = make_api_event(
            method="PATCH",
            path=f"/v1/orders/{order.order_id}/status",
            path_parameters={"orderId": order.order_id},
            body={"status": "DELIVERED"},
            claims={"sub": "ADMIN-001", "cognito:groups": "admin"},
        )
        response = lambda_handler(event, None)

        assert response["statusCode"] == 409
        body = json.loads(response["body"])
        assert body["error"]["code"] == "CONFLICT"
        assert "Cannot transition from PENDING to DELIVERED" in body["error"]["message"]


@mock_aws
class TestHealthHandler:
    def test_health(self):
        from src.handlers.health import lambda_handler

        response = lambda_handler({}, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["status"] == "healthy"
