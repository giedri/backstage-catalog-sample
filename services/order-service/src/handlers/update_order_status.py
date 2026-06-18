import json
import logging
import os

from src.models.order import InvalidTransitionError
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
        body = json.loads(event.get("body", "{}"))
        new_status = body.get("status")

        if not new_status:
            return error("BAD_REQUEST", "status is required", 400)

        # Fetch order first to get customer_id for auth check
        order = service.get_order(order_id)

        # Require owner or admin authorization
        require_owner_or_admin(event, order.customer_id)

        updated_order = service.update_order_status(order_id, new_status)
        return success(updated_order.to_api_response())

    except AuthError as e:
        return error(e.code, e.message, 401 if e.code == "UNAUTHORIZED" else 403)
    except OrderNotFoundError:
        return error("NOT_FOUND", "Order not found", 404)
    except InvalidTransitionError as e:
        return error("INVALID_TRANSITION", str(e), 400)
    except ValueError as e:
        logger.warning("Invalid status: %s", e)
        return error("BAD_REQUEST", f"Invalid status: {e}", 400)
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning("Invalid request: %s", e)
        return error("BAD_REQUEST", f"Invalid request: {e}", 400)
    except Exception:
        logger.exception("Unhandled error in update_order_status")
        return error("INTERNAL_ERROR", "Internal server error", 500)
