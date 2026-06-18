import pytest
from moto import mock_aws

from src.models.order import InvalidTransitionError, OrderStatus
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

    # --- Valid transition tests ---

    def test_transition_pending_to_confirmed(self, order_service):
        order = order_service.create_order(customer_id="CUST-001", items=SAMPLE_ITEMS)
        updated = order_service.update_order_status(order.order_id, "CONFIRMED")
        assert updated.status == OrderStatus.CONFIRMED

    def test_transition_pending_to_cancelled(self, order_service):
        order = order_service.create_order(customer_id="CUST-001", items=SAMPLE_ITEMS)
        updated = order_service.update_order_status(order.order_id, "CANCELLED")
        assert updated.status == OrderStatus.CANCELLED

    def test_transition_confirmed_to_shipped(self, order_service):
        order = order_service.create_order(customer_id="CUST-001", items=SAMPLE_ITEMS)
        order_service.update_order_status(order.order_id, "CONFIRMED")
        updated = order_service.update_order_status(order.order_id, "SHIPPED")
        assert updated.status == OrderStatus.SHIPPED

    def test_transition_confirmed_to_cancelled(self, order_service):
        order = order_service.create_order(customer_id="CUST-001", items=SAMPLE_ITEMS)
        order_service.update_order_status(order.order_id, "CONFIRMED")
        updated = order_service.update_order_status(order.order_id, "CANCELLED")
        assert updated.status == OrderStatus.CANCELLED

    def test_transition_shipped_to_delivered(self, order_service):
        order = order_service.create_order(customer_id="CUST-001", items=SAMPLE_ITEMS)
        order_service.update_order_status(order.order_id, "CONFIRMED")
        order_service.update_order_status(order.order_id, "SHIPPED")
        updated = order_service.update_order_status(order.order_id, "DELIVERED")
        assert updated.status == OrderStatus.DELIVERED

    # --- Invalid transition tests ---

    def test_transition_pending_to_shipped_invalid(self, order_service):
        order = order_service.create_order(customer_id="CUST-001", items=SAMPLE_ITEMS)
        with pytest.raises(InvalidTransitionError) as exc_info:
            order_service.update_order_status(order.order_id, "SHIPPED")
        assert "PENDING" in str(exc_info.value)
        assert "SHIPPED" in str(exc_info.value)

    def test_transition_pending_to_delivered_invalid(self, order_service):
        order = order_service.create_order(customer_id="CUST-001", items=SAMPLE_ITEMS)
        with pytest.raises(InvalidTransitionError) as exc_info:
            order_service.update_order_status(order.order_id, "DELIVERED")
        assert "PENDING" in str(exc_info.value)
        assert "DELIVERED" in str(exc_info.value)

    def test_transition_delivered_to_cancelled_invalid(self, order_service):
        order = order_service.create_order(customer_id="CUST-001", items=SAMPLE_ITEMS)
        order_service.update_order_status(order.order_id, "CONFIRMED")
        order_service.update_order_status(order.order_id, "SHIPPED")
        order_service.update_order_status(order.order_id, "DELIVERED")
        with pytest.raises(InvalidTransitionError) as exc_info:
            order_service.update_order_status(order.order_id, "CANCELLED")
        assert "DELIVERED" in str(exc_info.value)
        assert "CANCELLED" in str(exc_info.value)

    def test_transition_cancelled_to_pending_invalid(self, order_service):
        order = order_service.create_order(customer_id="CUST-001", items=SAMPLE_ITEMS)
        order_service.update_order_status(order.order_id, "CANCELLED")
        with pytest.raises(InvalidTransitionError) as exc_info:
            order_service.update_order_status(order.order_id, "PENDING")
        assert "CANCELLED" in str(exc_info.value)
        assert "PENDING" in str(exc_info.value)

    def test_terminal_state_delivered_no_transitions(self, order_service):
        order = order_service.create_order(customer_id="CUST-001", items=SAMPLE_ITEMS)
        order_service.update_order_status(order.order_id, "CONFIRMED")
        order_service.update_order_status(order.order_id, "SHIPPED")
        order_service.update_order_status(order.order_id, "DELIVERED")
        # Try all statuses from DELIVERED - all should fail
        for status in ["PENDING", "CONFIRMED", "SHIPPED", "CANCELLED"]:
            with pytest.raises(InvalidTransitionError):
                order_service.update_order_status(order.order_id, status)

    def test_terminal_state_cancelled_no_transitions(self, order_service):
        order = order_service.create_order(customer_id="CUST-001", items=SAMPLE_ITEMS)
        order_service.update_order_status(order.order_id, "CANCELLED")
        # Try all statuses from CANCELLED - all should fail
        for status in ["PENDING", "CONFIRMED", "SHIPPED", "DELIVERED"]:
            with pytest.raises(InvalidTransitionError):
                order_service.update_order_status(order.order_id, status)
