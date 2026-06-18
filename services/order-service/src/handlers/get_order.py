import json
import logging
import os

from src.services.order_service import OrderNotFoundError, OrderService
from src.utils.auth import AuthError, require_owner_or_admin
from src.utils.response import error, success

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

service = OrderService(table_name=os.environ.get("TABLE_NAME", "orders"))


def lambda_handler(event, context):
    logger.debug("Event: %s", json.dumps(event))
    try:
        order_id = event["pathParameters"]["orderId"]
        order = service.get_order(order_id)

        # Verify the authenticated user owns this order (or is admin)
        require_owner_or_admin(event, order.customer_id)

        return success(order.to_api_response())

    except AuthError as e:
        return error(e.code, e.message, 401 if e.code == "UNAUTHORIZED" else 403)
    except OrderNotFoundError:
        return error("NOT_FOUND", "Order not found", 404)
    except KeyError as e:
        logger.warning("Missing parameter: %s", e)
        return error("BAD_REQUEST", f"Missing parameter: {e}", 400)
    except Exception:
        logger.exception("Unhandled error in get_order")
        return error("INTERNAL_ERROR", "Internal server error", 500)
