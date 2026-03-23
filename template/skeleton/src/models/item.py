from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


@dataclass
class Item:
    """Generic item model. Rename and extend for your domain entity."""

    name: str
    description: str
    owner_id: str
    item_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dynamodb_item(self) -> dict:
        return {
            "pk": f"ITEM#{self.item_id}",
            "sk": f"ITEM#{self.item_id}",
            "gsi1pk": f"OWNER#{self.owner_id}",
            "gsi1sk": f"ITEM#{self.created_at}",
            "item_id": self.item_id,
            "#name": self.name,
            "description": self.description,
            "owner_id": self.owner_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dynamodb_item(cls, item: dict) -> Item:
        return cls(
            item_id=item["item_id"],
            name=item.get("item_name", item.get("#name", "")),
            description=item.get("description", ""),
            owner_id=item["owner_id"],
            created_at=item["created_at"],
            updated_at=item["updated_at"],
        )

    def to_api_response(self) -> dict:
        return {
            "item_id": self.item_id,
            "name": self.name,
            "description": self.description,
            "owner_id": self.owner_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
