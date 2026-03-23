import pytest
from moto import mock_aws

from src.models.order import OrderStatus
from src.services.order_service import OrderConflictError, OrderNotFoundError


SAMPLE_ITEMS = [
    {
        "product_id": "PROD-001",
        "product_name": "Widget",
        "quantity": 2,
        "unit_price": 9.99,
    },
    {
        "product_id": "PROD-002",
        "product_name": "Gadget",
        "quantity": 1,
        "unit_price": 24.99,
    },
]


@mock_aws
class TestOrderService:
    def test_create_order(self, order_service):
        order = order_service.create_order(customer_id="CUST-001", items=SAMPLE_ITEMS)

        assert order.customer_id == "CUST-001"
        assert order.status == OrderStatus.PENDING
        assert len(order.items) == 2
        assert order.total_amount == pytest.approx(44.97)

    def test_get_order(self, order_service):
        created = order_service.create_order(customer_id="CUST-001", items=SAMPLE_ITEMS)
        fetched = order_service.get_order(created.order_id)

        assert fetched.order_id == created.order_id
        assert fetched.customer_id == "CUST-001"
        assert fetched.status == OrderStatus.PENDING

    def test_get_order_not_found(self, order_service):
        with pytest.raises(OrderNotFoundError):
            order_service.get_order("nonexistent-id")

    def test_list_orders(self, order_service):
        order_service.create_order(customer_id="CUST-001", items=SAMPLE_ITEMS)
        order_service.create_order(customer_id="CUST-001", items=SAMPLE_ITEMS)
        order_service.create_order(customer_id="CUST-002", items=SAMPLE_ITEMS)

        orders, next_token = order_service.list_orders(customer_id="CUST-001")

        assert len(orders) == 2
        assert all(o.customer_id == "CUST-001" for o in orders)
        assert next_token is None

    def test_list_orders_pagination(self, order_service):
        for _ in range(3):
            order_service.create_order(customer_id="CUST-001", items=SAMPLE_ITEMS)

        orders, next_token = order_service.list_orders(customer_id="CUST-001", limit=2)

        assert len(orders) == 2
        assert next_token is not None

        orders2, next_token2 = order_service.list_orders(
            customer_id="CUST-001", limit=2, next_token=next_token
        )
        assert len(orders2) == 1
        assert next_token2 is None

    def test_update_order_status(self, order_service):
        created = order_service.create_order(customer_id="CUST-001", items=SAMPLE_ITEMS)
        updated = order_service.update_order_status(created.order_id, "CONFIRMED")

        assert updated.status == OrderStatus.CONFIRMED
        assert updated.updated_at > created.updated_at

    def test_update_order_status_not_found(self, order_service):
        with pytest.raises(OrderNotFoundError):
            order_service.update_order_status("nonexistent-id", "CONFIRMED")

    def test_update_order_status_invalid(self, order_service):
        created = order_service.create_order(customer_id="CUST-001", items=SAMPLE_ITEMS)
        with pytest.raises(ValueError):
            order_service.update_order_status(created.order_id, "INVALID")
