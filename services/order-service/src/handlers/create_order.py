import json
import logging
import os

from src.services.order_service import OrderConflictError, OrderService
from src.utils.auth import AuthError, get_user_id
from src.utils.response import error, success

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

service = OrderService(table_name=os.environ.get("TABLE_NAME", "orders"))


def lambda_handler(event, context):
    logger.debug("Event: %s", json.dumps(event))
    try:
        # Use authenticated user's sub as customer_id
        customer_id = get_user_id(event)

        body = json.loads(event.get("body", "{}"))
        items = body.get("items")

        if not items:
            return error("BAD_REQUEST", "items are required", 400)

        order = service.create_order(customer_id=customer_id, items=items)
        return success(order.to_api_response(), 201)

    except AuthError as e:
        return error(e.code, e.message, 401 if e.code == "UNAUTHORIZED" else 403)
    except OrderConflictError as e:
        logger.warning("Conflict: %s", e)
        return error("CONFLICT", str(e), 409)
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.warning("Invalid request: %s", e)
        return error("BAD_REQUEST", f"Invalid request body: {e}", 400)
    except Exception:
        logger.exception("Unhandled error in create_order")
        return error("INTERNAL_ERROR", "Internal server error", 500)
