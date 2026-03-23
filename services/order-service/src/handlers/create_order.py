import json
import logging
import os

from src.services.order_service import OrderConflictError, OrderService
from src.utils.response import error, success

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

service = OrderService(table_name=os.environ.get("TABLE_NAME", "orders"))


def lambda_handler(event, context):
    logger.debug("Event: %s", json.dumps(event))
    try:
        body = json.loads(event.get("body", "{}"))
        customer_id = body.get("customer_id")
        items = body.get("items")

        if not customer_id or not items:
            return error("BAD_REQUEST", "customer_id and items are required", 400)

        order = service.create_order(customer_id=customer_id, items=items)
        return success(order.to_api_response(), 201)

    except OrderConflictError as e:
        logger.warning("Conflict: %s", e)
        return error("CONFLICT", str(e), 409)
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.warning("Invalid request: %s", e)
        return error("BAD_REQUEST", f"Invalid request body: {e}", 400)
    except Exception:
        logger.exception("Unhandled error in create_order")
        return error("INTERNAL_ERROR", "Internal server error", 500)
