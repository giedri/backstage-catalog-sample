"""Reusable input validation helpers.

These validators enforce strict type and value constraints on user-provided
input before it reaches the persistence layer. This prevents type-confusion
bugs (e.g., integer customer_id creating unretrievable DynamoDB records).
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def validate_customer_id(customer_id: Any) -> None:
    """Validate that customer_id is a non-empty string.

    Raises:
        ValueError: If customer_id is not a string or is empty/blank.
    """
    if not isinstance(customer_id, str):
        raise ValueError(
            f"customer_id must be a string, got {type(customer_id).__name__}"
        )
    if not customer_id.strip():
        raise ValueError("customer_id must not be empty")


def validate_order_items(items: Any) -> None:
    """Validate the structure and types of order line items.

    Each item must contain:
      - product_id: non-empty string
      - product_name: non-empty string
      - quantity: positive integer
      - unit_price: positive number (int or float)

    Raises:
        ValueError: If items is not a list, is empty, or any item has
                    invalid/missing fields.
    """
    if not isinstance(items, list):
        raise ValueError("items must be a list")
    if not items:
        raise ValueError("items must not be empty")

    required_fields = {"product_id", "product_name", "quantity", "unit_price"}

    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f"items[{idx}] must be a dict")

        missing = required_fields - item.keys()
        if missing:
            raise ValueError(
                f"items[{idx}] missing required fields: {sorted(missing)}"
            )

        # product_id: must be a non-empty string
        if not isinstance(item["product_id"], str):
            raise ValueError(
                f"items[{idx}].product_id must be a string, "
                f"got {type(item['product_id']).__name__}"
            )
        if not item["product_id"].strip():
            raise ValueError(f"items[{idx}].product_id must not be empty")

        # product_name: must be a non-empty string
        if not isinstance(item["product_name"], str):
            raise ValueError(
                f"items[{idx}].product_name must be a string, "
                f"got {type(item['product_name']).__name__}"
            )
        if not item["product_name"].strip():
            raise ValueError(f"items[{idx}].product_name must not be empty")

        # quantity: must be a positive integer (not a bool)
        if isinstance(item["quantity"], bool) or not isinstance(item["quantity"], int):
            raise ValueError(
                f"items[{idx}].quantity must be an integer, "
                f"got {type(item['quantity']).__name__}"
            )
        if item["quantity"] <= 0:
            raise ValueError(f"items[{idx}].quantity must be positive")

        # unit_price: must be a positive number (int or float, not bool)
        if isinstance(item["unit_price"], bool) or not isinstance(
            item["unit_price"], (int, float)
        ):
            raise ValueError(
                f"items[{idx}].unit_price must be a number, "
                f"got {type(item['unit_price']).__name__}"
            )
        if item["unit_price"] <= 0:
            raise ValueError(f"items[{idx}].unit_price must be positive")
