import json
import logging
import os

from src.services.order_service import OrderService
from src.utils.response import error, success

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

service = OrderService(table_name=os.environ.get("TABLE_NAME", "orders"))


def lambda_handler(event, context):
    logger.debug("Event: %s", json.dumps(event))
    try:
        params = event.get("queryStringParameters") or {}
        customer_id = params.get("customer_id")

        if not customer_id:
            return error("BAD_REQUEST", "customer_id query parameter is required", 400)

        limit = min(int(params.get("limit", "20")), 100)
        next_token = params.get("next_token")

        orders, result_next_token = service.list_orders(
            customer_id=customer_id, limit=limit, next_token=next_token
        )

        response_body = {
            "items": [order.to_api_response() for order in orders],
        }
        if result_next_token:
            response_body["next_token"] = result_next_token

        return success(response_body)

    except ValueError as e:
        logger.warning("Invalid parameter: %s", e)
        return error("BAD_REQUEST", f"Invalid parameter: {e}", 400)
    except Exception:
        logger.exception("Unhandled error in list_orders")
        return error("INTERNAL_ERROR", "Internal server error", 500)
