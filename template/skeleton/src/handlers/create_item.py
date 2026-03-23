import json
import logging
import os

from src.services.item_service import ItemConflictError, ItemService
from src.utils.response import error, success

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

service = ItemService(table_name=os.environ.get("TABLE_NAME", "items"))


def lambda_handler(event, context):
    logger.debug("Event: %s", json.dumps(event))
    try:
        body = json.loads(event.get("body", "{}"))
        name = body.get("name")
        description = body.get("description", "")
        owner_id = body.get("owner_id")

        if not name or not owner_id:
            return error("BAD_REQUEST", "name and owner_id are required", 400)

        item = service.create_item(name=name, description=description, owner_id=owner_id)
        return success(item.to_api_response(), 201)

    except ItemConflictError as e:
        logger.warning("Conflict: %s", e)
        return error("CONFLICT", str(e), 409)
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.warning("Invalid request: %s", e)
        return error("BAD_REQUEST", f"Invalid request body: {e}", 400)
    except Exception:
        logger.exception("Unhandled error in create_item")
        return error("INTERNAL_ERROR", "Internal server error", 500)
