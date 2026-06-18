import json
import logging
import os

from src.services.item_service import ItemService
from src.utils.auth import UnauthorizedError, get_caller_identity
from src.utils.response import error, success

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

service = ItemService(table_name=os.environ.get("TABLE_NAME", "items"))


def lambda_handler(event, context):
    logger.debug("Event: %s", json.dumps(event))
    try:
        caller_id = get_caller_identity(event)

        params = event.get("queryStringParameters") or {}
        limit = min(int(params.get("limit", "20")), 100)
        next_token = params.get("next_token")

        items, result_next_token = service.list_items(
            owner_id=caller_id, limit=limit, next_token=next_token
        )

        response_body = {
            "items": [item.to_api_response() for item in items],
        }
        if result_next_token:
            response_body["next_token"] = result_next_token

        return success(response_body)

    except UnauthorizedError as e:
        logger.warning("Unauthorized: %s", e)
        return error("UNAUTHORIZED", str(e), 401)
    except ValueError as e:
        logger.warning("Invalid parameter: %s", e)
        return error("BAD_REQUEST", f"Invalid parameter: {e}", 400)
    except Exception:
        logger.exception("Unhandled error in list_items")
        return error("INTERNAL_ERROR", "Internal server error", 500)
