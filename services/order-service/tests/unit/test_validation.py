"""Unit tests for input validation helpers.

Tests cover:
- customer_id type enforcement (integer rejected, non-string rejected)
- customer_id emptiness check
- items list structure validation
- item field type enforcement (product_id, product_name as strings; quantity as int; unit_price as number)
- missing required fields
- valid input accepted without error
"""

from __future__ import annotations

import pytest

from src.utils.validation import validate_customer_id, validate_order_items


VALID_ITEM = {
    "product_id": "PROD-001",
    "product_name": "Widget",
    "quantity": 2,
    "unit_price": 9.99,
}


class TestValidateCustomerId:
    """Tests for validate_customer_id."""

    def test_valid_string_customer_id(self):
        """A normal string customer_id passes validation."""
        validate_customer_id("CUST-001")

    def test_valid_uuid_string(self):
        """A UUID-formatted string passes validation."""
        validate_customer_id("550e8400-e29b-41d4-a716-446655440000")

    def test_integer_customer_id_rejected(self):
        """An integer customer_id raises ValueError (the core bug scenario)."""
        with pytest.raises(ValueError, match="customer_id must be a string"):
            validate_customer_id(12345)

    def test_float_customer_id_rejected(self):
        """A float customer_id raises ValueError."""
        with pytest.raises(ValueError, match="customer_id must be a string"):
            validate_customer_id(12.5)

    def test_none_customer_id_rejected(self):
        """None customer_id raises ValueError."""
        with pytest.raises(ValueError, match="customer_id must be a string"):
            validate_customer_id(None)

    def test_bool_customer_id_rejected(self):
        """Boolean customer_id raises ValueError."""
        with pytest.raises(ValueError, match="customer_id must be a string"):
            validate_customer_id(True)

    def test_list_customer_id_rejected(self):
        """A list customer_id raises ValueError."""
        with pytest.raises(ValueError, match="customer_id must be a string"):
            validate_customer_id(["CUST-001"])

    def test_dict_customer_id_rejected(self):
        """A dict customer_id raises ValueError."""
        with pytest.raises(ValueError, match="customer_id must be a string"):
            validate_customer_id({"id": "CUST-001"})

    def test_empty_string_customer_id_rejected(self):
        """An empty string customer_id raises ValueError."""
        with pytest.raises(ValueError, match="customer_id must not be empty"):
            validate_customer_id("")

    def test_whitespace_only_customer_id_rejected(self):
        """A whitespace-only string customer_id raises ValueError."""
        with pytest.raises(ValueError, match="customer_id must not be empty"):
            validate_customer_id("   ")


class TestValidateOrderItems:
    """Tests for validate_order_items."""

    def test_valid_single_item(self):
        """A valid single-item list passes validation."""
        validate_order_items([VALID_ITEM])

    def test_valid_multiple_items(self):
        """A valid multi-item list passes validation."""
        items = [
            VALID_ITEM,
            {
                "product_id": "PROD-002",
                "product_name": "Gadget",
                "quantity": 1,
                "unit_price": 19.99,
            },
        ]
        validate_order_items(items)

    def test_valid_integer_unit_price(self):
        """An integer unit_price (e.g., 10) is accepted as a valid number."""
        item = {**VALID_ITEM, "unit_price": 10}
        validate_order_items([item])

    def test_items_not_a_list_rejected(self):
        """A non-list items value raises ValueError."""
        with pytest.raises(ValueError, match="items must be a list"):
            validate_order_items("not-a-list")

    def test_items_none_rejected(self):
        """None items value raises ValueError."""
        with pytest.raises(ValueError, match="items must be a list"):
            validate_order_items(None)

    def test_items_empty_list_rejected(self):
        """An empty list raises ValueError."""
        with pytest.raises(ValueError, match="items must not be empty"):
            validate_order_items([])

    def test_item_not_a_dict_rejected(self):
        """A non-dict item raises ValueError."""
        with pytest.raises(ValueError, match=r"items\[0\] must be a dict"):
            validate_order_items(["not-a-dict"])

    def test_missing_product_id_rejected(self):
        """An item missing product_id raises ValueError."""
        item = {
            "product_name": "Widget",
            "quantity": 2,
            "unit_price": 9.99,
        }
        with pytest.raises(ValueError, match="missing required fields"):
            validate_order_items([item])

    def test_missing_product_name_rejected(self):
        """An item missing product_name raises ValueError."""
        item = {
            "product_id": "PROD-001",
            "quantity": 2,
            "unit_price": 9.99,
        }
        with pytest.raises(ValueError, match="missing required fields"):
            validate_order_items([item])

    def test_missing_quantity_rejected(self):
        """An item missing quantity raises ValueError."""
        item = {
            "product_id": "PROD-001",
            "product_name": "Widget",
            "unit_price": 9.99,
        }
        with pytest.raises(ValueError, match="missing required fields"):
            validate_order_items([item])

    def test_missing_unit_price_rejected(self):
        """An item missing unit_price raises ValueError."""
        item = {
            "product_id": "PROD-001",
            "product_name": "Widget",
            "quantity": 2,
        }
        with pytest.raises(ValueError, match="missing required fields"):
            validate_order_items([item])

    def test_product_id_integer_rejected(self):
        """An integer product_id raises ValueError."""
        item = {**VALID_ITEM, "product_id": 123}
        with pytest.raises(ValueError, match="product_id must be a string"):
            validate_order_items([item])

    def test_product_id_empty_rejected(self):
        """An empty product_id raises ValueError."""
        item = {**VALID_ITEM, "product_id": ""}
        with pytest.raises(ValueError, match="product_id must not be empty"):
            validate_order_items([item])

    def test_product_name_integer_rejected(self):
        """An integer product_name raises ValueError."""
        item = {**VALID_ITEM, "product_name": 456}
        with pytest.raises(ValueError, match="product_name must be a string"):
            validate_order_items([item])

    def test_product_name_empty_rejected(self):
        """An empty product_name raises ValueError."""
        item = {**VALID_ITEM, "product_name": "   "}
        with pytest.raises(ValueError, match="product_name must not be empty"):
            validate_order_items([item])

    def test_quantity_string_rejected(self):
        """A string quantity raises ValueError."""
        item = {**VALID_ITEM, "quantity": "two"}
        with pytest.raises(ValueError, match="quantity must be an integer"):
            validate_order_items([item])

    def test_quantity_float_rejected(self):
        """A float quantity raises ValueError."""
        item = {**VALID_ITEM, "quantity": 2.5}
        with pytest.raises(ValueError, match="quantity must be an integer"):
            validate_order_items([item])

    def test_quantity_bool_rejected(self):
        """A boolean quantity raises ValueError."""
        item = {**VALID_ITEM, "quantity": True}
        with pytest.raises(ValueError, match="quantity must be an integer"):
            validate_order_items([item])

    def test_quantity_zero_rejected(self):
        """A zero quantity raises ValueError."""
        item = {**VALID_ITEM, "quantity": 0}
        with pytest.raises(ValueError, match="quantity must be positive"):
            validate_order_items([item])

    def test_quantity_negative_rejected(self):
        """A negative quantity raises ValueError."""
        item = {**VALID_ITEM, "quantity": -1}
        with pytest.raises(ValueError, match="quantity must be positive"):
            validate_order_items([item])

    def test_unit_price_string_rejected(self):
        """A string unit_price raises ValueError."""
        item = {**VALID_ITEM, "unit_price": "9.99"}
        with pytest.raises(ValueError, match="unit_price must be a number"):
            validate_order_items([item])

    def test_unit_price_bool_rejected(self):
        """A boolean unit_price raises ValueError."""
        item = {**VALID_ITEM, "unit_price": True}
        with pytest.raises(ValueError, match="unit_price must be a number"):
            validate_order_items([item])

    def test_unit_price_zero_rejected(self):
        """A zero unit_price raises ValueError."""
        item = {**VALID_ITEM, "unit_price": 0}
        with pytest.raises(ValueError, match="unit_price must be positive"):
            validate_order_items([item])

    def test_unit_price_negative_rejected(self):
        """A negative unit_price raises ValueError."""
        item = {**VALID_ITEM, "unit_price": -5.00}
        with pytest.raises(ValueError, match="unit_price must be positive"):
            validate_order_items([item])

    def test_second_item_invalid_caught(self):
        """Validation error in the second item is properly reported."""
        items = [
            VALID_ITEM,
            {**VALID_ITEM, "product_id": 999},
        ]
        with pytest.raises(ValueError, match=r"items\[1\]\.product_id must be a string"):
            validate_order_items(items)
