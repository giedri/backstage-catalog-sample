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
            claims={"customer_id": "CUST-001"},
        )
        response = lambda_handler(event, None)

        assert response["statusCode"] == 201
        body = json.loads(response["body"])
        assert body["customer_id"] == "CUST-001"
        assert body["status"] == "PENDING"

    def test_create_order_missing_fields(self, dynamodb_table):
        from src.handlers.create_order import lambda_handler

        event = make_api_event(
            method="POST",
            path="/v1/orders",
            body={},
            claims={"customer_id": "CUST-001"},
        )
        response = lambda_handler(event, None)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["error"]["code"] == "BAD_REQUEST"

    def test_create_order_forbidden_different_customer(self, dynamodb_table):
        from src.handlers.create_order import lambda_handler

        event = make_api_event(
            method="POST",
            path="/v1/orders",
            body={"customer_id": "CUST-002", "items": SAMPLE_ITEMS},
            claims={"customer_id": "CUST-001"},
        )
        response = lambda_handler(event, None)

        assert response["statusCode"] == 403
        body = json.loads(response["body"])
        assert body["error"]["code"] == "FORBIDDEN"

    def test_create_order_forbidden_missing_claims(self, dynamodb_table):
        from src.handlers.create_order import lambda_handler

        event = make_api_event(
            method="POST",
            path="/v1/orders",
            body={"customer_id": "CUST-001", "items": SAMPLE_ITEMS},
        )
        response = lambda_handler(event, None)

        assert response["statusCode"] == 403
        body = json.loads(response["body"])
        assert body["error"]["code"] == "FORBIDDEN"


@mock_aws
class TestGetOrderHandler:
    def test_get_order_not_found(self, dynamodb_table):
        from src.handlers.get_order import lambda_handler

        event = make_api_event(
            method="GET",
            path="/v1/orders/nonexistent",
            path_parameters={"orderId": "nonexistent"},
            claims={"customer_id": "CUST-001"},
        )
        response = lambda_handler(event, None)

        assert response["statusCode"] == 404

    def test_get_order_success(self, dynamodb_table, order_service):
        from src.handlers.get_order import lambda_handler

        order = order_service.create_order(
            customer_id="CUST-001", items=SAMPLE_ITEMS
        )

        event = make_api_event(
            method="GET",
            path=f"/v1/orders/{order.order_id}",
            path_parameters={"orderId": order.order_id},
            claims={"customer_id": "CUST-001"},
        )
        response = lambda_handler(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["order_id"] == order.order_id
        assert body["customer_id"] == "CUST-001"

    def test_get_order_forbidden_different_customer(self, dynamodb_table, order_service):
        from src.handlers.get_order import lambda_handler

        order = order_service.create_order(
            customer_id="CUST-001", items=SAMPLE_ITEMS
        )

        event = make_api_event(
            method="GET",
            path=f"/v1/orders/{order.order_id}",
            path_parameters={"orderId": order.order_id},
            claims={"customer_id": "CUST-999"},
        )
        response = lambda_handler(event, None)

        # Returns 404 (not 403) to avoid leaking order existence
        assert response["statusCode"] == 404
        body = json.loads(response["body"])
        assert body["error"]["code"] == "NOT_FOUND"

    def test_get_order_forbidden_missing_claims(self, dynamodb_table, order_service):
        from src.handlers.get_order import lambda_handler

        order = order_service.create_order(
            customer_id="CUST-001", items=SAMPLE_ITEMS
        )

        event = make_api_event(
            method="GET",
            path=f"/v1/orders/{order.order_id}",
            path_parameters={"orderId": order.order_id},
        )
        response = lambda_handler(event, None)

        # Returns 404 when claims are missing (fail-closed)
        assert response["statusCode"] == 404
        body = json.loads(response["body"])
        assert body["error"]["code"] == "NOT_FOUND"


@mock_aws
class TestListOrdersHandler:
    def test_list_orders_missing_customer(self, dynamodb_table):
        from src.handlers.list_orders import lambda_handler

        event = make_api_event(
            method="GET",
            path="/v1/orders",
            claims={"customer_id": "CUST-001"},
        )
        response = lambda_handler(event, None)

        assert response["statusCode"] == 400

    def test_list_orders_success(self, dynamodb_table, order_service):
        from src.handlers.list_orders import lambda_handler

        order_service.create_order(customer_id="CUST-001", items=SAMPLE_ITEMS)

        event = make_api_event(
            method="GET",
            path="/v1/orders",
            query_string_parameters={"customer_id": "CUST-001"},
            claims={"customer_id": "CUST-001"},
        )
        response = lambda_handler(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert len(body["items"]) == 1

    def test_list_orders_forbidden_different_customer(self, dynamodb_table):
        from src.handlers.list_orders import lambda_handler

        event = make_api_event(
            method="GET",
            path="/v1/orders",
            query_string_parameters={"customer_id": "CUST-002"},
            claims={"customer_id": "CUST-001"},
        )
        response = lambda_handler(event, None)

        assert response["statusCode"] == 403
        body = json.loads(response["body"])
        assert body["error"]["code"] == "FORBIDDEN"

    def test_list_orders_forbidden_missing_claims(self, dynamodb_table):
        from src.handlers.list_orders import lambda_handler

        event = make_api_event(
            method="GET",
            path="/v1/orders",
            query_string_parameters={"customer_id": "CUST-001"},
        )
        response = lambda_handler(event, None)

        assert response["statusCode"] == 403
        body = json.loads(response["body"])
        assert body["error"]["code"] == "FORBIDDEN"


@mock_aws
class TestUpdateOrderStatusHandler:
    def test_update_order_status_success(self, dynamodb_table, order_service):
        from src.handlers.update_order_status import lambda_handler

        order = order_service.create_order(
            customer_id="CUST-001", items=SAMPLE_ITEMS
        )

        event = make_api_event(
            method="PATCH",
            path=f"/v1/orders/{order.order_id}/status",
            path_parameters={"orderId": order.order_id},
            body={"status": "CONFIRMED"},
            claims={"customer_id": "CUST-001"},
        )
        response = lambda_handler(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["status"] == "CONFIRMED"

    def test_update_order_status_forbidden_different_customer(
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
            claims={"customer_id": "CUST-999"},
        )
        response = lambda_handler(event, None)

        # Returns 404 (not 403) to avoid leaking order existence
        assert response["statusCode"] == 404
        body = json.loads(response["body"])
        assert body["error"]["code"] == "NOT_FOUND"

    def test_update_order_status_not_found(self, dynamodb_table):
        from src.handlers.update_order_status import lambda_handler

        event = make_api_event(
            method="PATCH",
            path="/v1/orders/nonexistent/status",
            path_parameters={"orderId": "nonexistent"},
            body={"status": "CONFIRMED"},
            claims={"customer_id": "CUST-001"},
        )
        response = lambda_handler(event, None)

        assert response["statusCode"] == 404

    def test_update_order_status_missing_status(self, dynamodb_table, order_service):
        from src.handlers.update_order_status import lambda_handler

        order = order_service.create_order(
            customer_id="CUST-001", items=SAMPLE_ITEMS
        )

        event = make_api_event(
            method="PATCH",
            path=f"/v1/orders/{order.order_id}/status",
            path_parameters={"orderId": order.order_id},
            body={},
            claims={"customer_id": "CUST-001"},
        )
        response = lambda_handler(event, None)

        assert response["statusCode"] == 400

    def test_update_order_status_forbidden_missing_claims(
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
        )
        response = lambda_handler(event, None)

        # Returns 404 when claims are missing (fail-closed)
        assert response["statusCode"] == 404
        body = json.loads(response["body"])
        assert body["error"]["code"] == "NOT_FOUND"


@mock_aws
class TestHealthHandler:
    def test_health(self):
        from src.handlers.health import lambda_handler

        response = lambda_handler({}, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["status"] == "healthy"
