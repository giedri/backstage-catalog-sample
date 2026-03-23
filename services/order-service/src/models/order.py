from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger(__name__)


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


@dataclass
class OrderItem:
    product_id: str
    product_name: str
    quantity: int
    unit_price: float

    def to_dynamodb_item(self) -> dict:
        return {
            "product_id": self.product_id,
            "product_name": self.product_name,
            "quantity": self.quantity,
            "unit_price": str(self.unit_price),
        }

    @classmethod
    def from_dynamodb_item(cls, item: dict) -> OrderItem:
        return cls(
            product_id=item["product_id"],
            product_name=item["product_name"],
            quantity=int(item["quantity"]),
            unit_price=float(item["unit_price"]),
        )


@dataclass
class Order:
    customer_id: str
    items: list[OrderItem]
    order_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: OrderStatus = OrderStatus.PENDING
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    total_amount: float = 0.0

    def __post_init__(self):
        if self.total_amount == 0.0 and self.items:
            self.total_amount = sum(item.quantity * item.unit_price for item in self.items)

    def to_dynamodb_item(self) -> dict:
        return {
            "pk": f"ORDER#{self.order_id}",
            "sk": f"ORDER#{self.order_id}",
            "gsi1pk": f"CUSTOMER#{self.customer_id}",
            "gsi1sk": f"ORDER#{self.created_at}",
            "order_id": self.order_id,
            "customer_id": self.customer_id,
            "#status": self.status.value,
            "items": [item.to_dynamodb_item() for item in self.items],
            "total_amount": str(self.total_amount),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dynamodb_item(cls, item: dict) -> Order:
        return cls(
            order_id=item["order_id"],
            customer_id=item["customer_id"],
            status=OrderStatus(item.get("status", item.get("#status", "PENDING"))),
            items=[OrderItem.from_dynamodb_item(i) for i in item.get("items", [])],
            total_amount=float(item.get("total_amount", 0)),
            created_at=item["created_at"],
            updated_at=item["updated_at"],
        )

    def to_api_response(self) -> dict:
        return {
            "order_id": self.order_id,
            "customer_id": self.customer_id,
            "status": self.status.value,
            "items": [
                {
                    "product_id": item.product_id,
                    "product_name": item.product_name,
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                }
                for item in self.items
            ],
            "total_amount": self.total_amount,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
