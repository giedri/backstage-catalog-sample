import json
import logging
import os

from src.services.order_service import OrderNotFoundError, OrderService
from src.utils.auth import AuthError, get_user_claims
from src.utils.response import error, success

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

service = OrderService(table_name=os.environ.get("TABLE_NAME", "orders"))


def lambda_handler(event, context):
    logger.debug("Event: %s", json.dumps(event))
    try:
        order_id = event["pathParameters"]["orderId"]
        claims = get_user_claims(event)
        user_id = claims["sub"]
        is_admin_user = "admin" in claims["groups"]

        order = service.get_order(order_id)

        # Non-admin users can only see their own orders; return 404 to avoid info leak
        if not is_admin_user and order.customer_id != user_id:
            return error("NOT_FOUND", "Order not found", 404)

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
