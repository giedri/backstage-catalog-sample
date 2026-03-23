from __future__ import annotations

import logging
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

from src.models.order import Order, OrderItem, OrderStatus

logger = logging.getLogger(__name__)


class OrderNotFoundError(Exception):
    pass


class OrderConflictError(Exception):
    pass


class OrderService:
    def __init__(self, table_name: str, dynamodb_resource=None):
        self._dynamodb = dynamodb_resource or boto3.resource("dynamodb")
        self._table = self._dynamodb.Table(table_name)

    def create_order(self, customer_id: str, items: list[dict]) -> Order:
        order_items = [
            OrderItem(
                product_id=item["product_id"],
                product_name=item["product_name"],
                quantity=item["quantity"],
                unit_price=item["unit_price"],
            )
            for item in items
        ]
        order = Order(customer_id=customer_id, items=order_items)

        db_item = order.to_dynamodb_item()
        # DynamoDB reserved word: status
        db_item["order_status"] = db_item.pop("#status")

        try:
            self._table.put_item(
                Item=db_item,
                ConditionExpression="attribute_not_exists(pk)",
            )
        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                raise OrderConflictError(f"Order {order.order_id} already exists")
            raise

        logger.info("Created order %s for customer %s", order.order_id, customer_id)
        return order

    def get_order(self, order_id: str) -> Order:
        response = self._table.get_item(
            Key={"pk": f"ORDER#{order_id}", "sk": f"ORDER#{order_id}"},
        )
        item = response.get("Item")
        if not item:
            raise OrderNotFoundError(f"Order {order_id} not found")

        # Map stored field back to model field
        if "order_status" in item:
            item["#status"] = item.pop("order_status")

        return Order.from_dynamodb_item(item)

    def list_orders(
        self, customer_id: str, limit: int = 20, next_token: str | None = None
    ) -> tuple[list[Order], str | None]:
        kwargs = {
            "IndexName": "gsi1",
            "KeyConditionExpression": "#gsi1pk = :customer",
            "ExpressionAttributeNames": {"#gsi1pk": "gsi1pk"},
            "ExpressionAttributeValues": {":customer": f"CUSTOMER#{customer_id}"},
            "ScanIndexForward": False,
            "Limit": limit,
        }
        if next_token:
            import json
            import base64
            kwargs["ExclusiveStartKey"] = json.loads(base64.b64decode(next_token))

        response = self._table.query(**kwargs)
        items = response.get("Items", [])
        orders = []
        for item in items:
            if "order_status" in item:
                item["#status"] = item.pop("order_status")
            orders.append(Order.from_dynamodb_item(item))

        result_next_token = None
        if "LastEvaluatedKey" in response:
            import json
            import base64
            result_next_token = base64.b64encode(
                json.dumps(response["LastEvaluatedKey"]).encode()
            ).decode()

        logger.info("Listed %d orders for customer %s", len(orders), customer_id)
        return orders, result_next_token

    def update_order_status(self, order_id: str, new_status: str) -> Order:
        status = OrderStatus(new_status)
        now = datetime.now(timezone.utc).isoformat()

        try:
            response = self._table.update_item(
                Key={"pk": f"ORDER#{order_id}", "sk": f"ORDER#{order_id}"},
                UpdateExpression="SET order_status = :status, updated_at = :now",
                ExpressionAttributeValues={
                    ":status": status.value,
                    ":now": now,
                },
                ConditionExpression="attribute_exists(pk)",
                ReturnValues="ALL_NEW",
            )
        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                raise OrderNotFoundError(f"Order {order_id} not found")
            raise

        item = response["Attributes"]
        if "order_status" in item:
            item["#status"] = item.pop("order_status")

        logger.info("Updated order %s status to %s", order_id, status.value)
        return Order.from_dynamodb_item(item)
