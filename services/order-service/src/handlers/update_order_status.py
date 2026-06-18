import json
import logging
import os

from src.services.order_service import OrderAuthorizationError, OrderNotFoundError, OrderService
from src.utils.auth import get_customer_id_from_event
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

        # Extract authenticated customer_id from JWT claims
        customer_id = get_customer_id_from_event(event)
        if not customer_id:
            return error("NOT_FOUND", "Order not found", 404)

        # Single atomic operation: update status with customer_id ownership check.
        # This eliminates the separate get_order call for authorization.
        try:
            order = service.update_order_status(order_id, new_status, customer_id=customer_id)
        except OrderNotFoundError:
            return error("NOT_FOUND", "Order not found", 404)
        except OrderAuthorizationError:
            # Return 404 instead of 403 to avoid leaking order existence.
            # An unauthorized caller should not be able to distinguish between
            # "order does not exist" and "order belongs to someone else."
            return error("NOT_FOUND", "Order not found", 404)

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
