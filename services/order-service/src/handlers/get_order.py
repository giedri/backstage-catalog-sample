import json
import logging
import os

from src.services.order_service import OrderNotFoundError, OrderService
from src.utils.auth import get_customer_id_from_event
from src.utils.response import error, success

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

service = OrderService(table_name=os.environ.get("TABLE_NAME", "orders"))


def lambda_handler(event, context):
    logger.debug("Event: %s", json.dumps(event))
    try:
        order_id = event["pathParameters"]["orderId"]

        # Extract authenticated customer_id from JWT claims first.
        # Fail-closed: if claims are missing or invalid, return 404 immediately
        # so an unauthenticated caller cannot probe order existence.
        customer_id = get_customer_id_from_event(event)
        if not customer_id:
            return error("NOT_FOUND", "Order not found", 404)

        try:
            order = service.get_order(order_id)
        except OrderNotFoundError:
            return error("NOT_FOUND", "Order not found", 404)

        if order.customer_id != customer_id:
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
