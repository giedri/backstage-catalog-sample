# Coding Conventions

## Python Standards

- **Python 3.12** — use modern syntax (`from __future__ import annotations`, `X | Y` union types)
- **Type hints** required on all function signatures
- **Dataclasses** for models (not Pydantic or plain dicts)
- **Enums** use `(str, Enum)` pattern for JSON/DynamoDB serialization compatibility
- **Logging** via stdlib `logging` with configurable `LOG_LEVEL` environment variable

## Lambda Handler Pattern

Each handler maps to one HTTP method + resource path. Keep handlers **thin** — parse input, delegate to service, format response.

```python
import json
import logging
import os

from src.services.order_service import OrderNotFoundError, OrderService
from src.utils.response import error, success

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

# Module-level instantiation for Lambda cold-start optimization
service = OrderService(table_name=os.environ.get("TABLE_NAME", "orders"))


def lambda_handler(event, context):
    logger.debug("Event: %s", json.dumps(event))
    try:
        # Parse input from event
        # Call service layer
        # Return formatted response via success() helper
        pass
    except SpecificError as e:
        return error("ERROR_CODE", str(e), 4xx)
    except Exception:
        logger.exception("Unhandled error in handler_name")
        return error("INTERNAL_ERROR", "Internal server error", 500)
```

### Handler Rules
- Service instantiation at module level (reused across warm invocations)
- Always log the raw event at DEBUG level
- Catch specific exceptions → map to appropriate HTTP status codes
- Catch-all `Exception` → 500 with `logger.exception()` for stack trace
- Never expose internal error details to clients

## Model Pattern (Dataclasses)

#[[file:services/order-service/src/models/order.py]]

Models follow this structure:
- `@dataclass` with `field(default_factory=...)` for auto-generated values (UUID, timestamps)
- `__post_init__` for computed fields (e.g., `total_amount`)
- `to_dynamodb_item()` — serialize to DynamoDB item format
- `from_dynamodb_item(cls, item)` — class method to deserialize from DynamoDB
- `to_api_response()` — format for HTTP response (excludes internal fields like pk/sk)

## Service Layer Pattern

- Constructor injection for DynamoDB resource (`dynamodb_resource=None` with default fallback)
- Custom exception classes for domain errors: `OrderNotFoundError`, `OrderConflictError`
- Idempotent writes using `ConditionExpression="attribute_not_exists(pk)"`
- All DynamoDB interactions happen in the service layer (not handlers)

## DynamoDB Conventions

| Convention | Detail |
|-----------|--------|
| Key format | `pk = ENTITY#<id>`, `sk = ENTITY#<id>` |
| GSI format | `gsi1pk = PARENT_ENTITY#<id>`, `gsi1sk = ENTITY#<sort_value>` |
| Reserved words | Use `ExpressionAttributeNames` with `#placeholder` for `status`, `name`, `type`, `data` |
| Storage mapping | `status` field stored as `order_status` in DynamoDB (rename on read/write) |
| Amounts | Stored as strings for decimal precision |
| Pagination | Cursor-based with base64-encoded `LastEvaluatedKey` |
| Idempotency | Conditional writes: `attribute_not_exists(pk)` |
| TTL | Unix epoch integer in `ttl` attribute (reserved for future use) |

## Response Utilities

Use the shared response helpers in `src/utils/response.py`:

```python
from src.utils.response import success, error

# Success response
return success(body_dict, status_code=200)

# Error response
return error("ERROR_CODE", "Human-readable message", status_code=400)
```

Both helpers set `Content-Type: application/json` header automatically.

## File Organization

```
src/
├── handlers/          # One file per API endpoint (lambda entry point)
├── models/            # Data models with serialization methods
├── services/          # Business logic (called by handlers)
└── utils/             # Shared utilities (response helpers, validators)
```

- **No cross-handler imports** — handlers are independent Lambda functions
- **Services may import models** — services depend on models
- **Handlers import services and utils** — handlers are the composition root
