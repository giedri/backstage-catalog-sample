from __future__ import annotations

import base64
import json
import logging
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

from src.models.item import Item

logger = logging.getLogger(__name__)


class ItemNotFoundError(Exception):
    pass


class ItemConflictError(Exception):
    pass


class ItemService:
    """Generic CRUD service. Rename and extend for your domain entity."""

    def __init__(self, table_name: str, dynamodb_resource=None):
        self._dynamodb = dynamodb_resource or boto3.resource("dynamodb")
        self._table = self._dynamodb.Table(table_name)

    def create_item(self, name: str, description: str, owner_id: str) -> Item:
        item = Item(name=name, description=description, owner_id=owner_id)

        db_item = item.to_dynamodb_item()
        # DynamoDB reserved word: name
        db_item["item_name"] = db_item.pop("#name")

        try:
            self._table.put_item(
                Item=db_item,
                ConditionExpression="attribute_not_exists(pk)",
            )
        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                raise ItemConflictError(f"Item {item.item_id} already exists")
            raise

        logger.info("Created item %s for owner %s", item.item_id, owner_id)
        return item

    def get_item(self, item_id: str) -> Item:
        response = self._table.get_item(
            Key={"pk": f"ITEM#{item_id}", "sk": f"ITEM#{item_id}"},
        )
        db_item = response.get("Item")
        if not db_item:
            raise ItemNotFoundError(f"Item {item_id} not found")

        return Item.from_dynamodb_item(db_item)

    def list_items(
        self, owner_id: str, limit: int = 20, next_token: str | None = None
    ) -> tuple[list[Item], str | None]:
        kwargs = {
            "IndexName": "gsi1",
            "KeyConditionExpression": "#gsi1pk = :owner",
            "ExpressionAttributeNames": {"#gsi1pk": "gsi1pk"},
            "ExpressionAttributeValues": {":owner": f"OWNER#{owner_id}"},
            "ScanIndexForward": False,
            "Limit": limit,
        }
        if next_token:
            kwargs["ExclusiveStartKey"] = json.loads(base64.b64decode(next_token))

        response = self._table.query(**kwargs)
        items = [Item.from_dynamodb_item(i) for i in response.get("Items", [])]

        result_next_token = None
        if "LastEvaluatedKey" in response:
            result_next_token = base64.b64encode(
                json.dumps(response["LastEvaluatedKey"]).encode()
            ).decode()

        logger.info("Listed %d items for owner %s", len(items), owner_id)
        return items, result_next_token

    def delete_item(self, item_id: str) -> None:
        try:
            self._table.delete_item(
                Key={"pk": f"ITEM#{item_id}", "sk": f"ITEM#{item_id}"},
                ConditionExpression="attribute_exists(pk)",
            )
        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                raise ItemNotFoundError(f"Item {item_id} not found")
            raise

        logger.info("Deleted item %s", item_id)
