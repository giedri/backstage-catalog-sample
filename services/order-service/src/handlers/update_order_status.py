import json
import logging
import os

from src.services.order_service import OrderNotFoundError, OrderService
from src.utils.auth import authorize_customer_access
from src.utils.response import error, success

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

service = OrderService(table_name=os.environ.get("TABLE_NAME", "orders"))


def lambda_handler(event, context):
    logger.debug("Event: %s", json.dumps(event))
    try:
        order_id = event["pathParameters"]["orderId"]
        body = json.loads(event.get("body", "{}"))
        new_status = body.get("status")

        if not new_status:
            return error("BAD_REQUEST", "status is required", 400)

        # Fetch order first to verify ownership before updating
        try:
            order = service.get_order(order_id)
        except OrderNotFoundError:
            return error("NOT_FOUND", "Order not found", 404)

        is_authorized, _ = authorize_customer_access(event, order.customer_id)
        if not is_authorized:
            # Return 404 instead of 403 to avoid leaking order existence.
            # An unauthorized caller should not be able to distinguish between
            # "order does not exist" and "order belongs to someone else."
            return error("NOT_FOUND", "Order not found", 404)

        order = service.update_order_status(order_id, new_status)
        return success(order.to_api_response())

    except ValueError as e:
        logger.warning("Invalid status: %s", e)
        return error("BAD_REQUEST", f"Invalid status: {e}", 400)
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning("Invalid request: %s", e)
        return error("BAD_REQUEST", f"Invalid request: {e}", 400)
    except Exception:
        logger.exception("Unhandled error in update_order_status")
        return error("INTERNAL_ERROR", "Internal server error", 500)
