import json
import logging
import os

from src.services.item_service import ItemNotFoundError, ItemService
from src.utils.response import error

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

service = ItemService(table_name=os.environ.get("TABLE_NAME", "items"))


def lambda_handler(event, context):
    logger.debug("Event: %s", json.dumps(event))
    try:
        item_id = event["pathParameters"]["itemId"]
        service.delete_item(item_id)
        return {"statusCode": 204, "body": ""}

    except ItemNotFoundError:
        return error("NOT_FOUND", "Item not found", 404)
    except KeyError as e:
        logger.warning("Missing parameter: %s", e)
        return error("BAD_REQUEST", f"Missing parameter: {e}", 400)
    except Exception:
        logger.exception("Unhandled error in delete_item")
        return error("INTERNAL_ERROR", "Internal server error", 500)
