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

        return success(order.to_api_response())

    except KeyError as e:
        logger.warning("Missing parameter: %s", e)
        return error("BAD_REQUEST", f"Missing parameter: {e}", 400)
    except Exception:
        logger.exception("Unhandled error in get_order")
        return error("INTERNAL_ERROR", "Internal server error", 500)
