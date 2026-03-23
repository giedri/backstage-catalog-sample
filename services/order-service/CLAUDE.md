<!-- claude-hub:fragment:begin — This section is managed centrally. Do not edit manually. Run /hub-fragment-update to update. -->
# SAM API Service — Toolchain Reference

## Commands

### Build and Deploy
```bash
sam build                          # Build all functions and layers
sam build --use-container          # Build in Docker (correct Python version)
sam validate --lint                # Validate template.yaml
sam deploy                         # Deploy using samconfig.toml
sam deploy --guided                # Interactive first-time deploy
sam delete                         # Tear down the stack
```

### Local Development
```bash
sam local start-api                                   # Start local API Gateway on port 3000
sam local invoke FunctionName -e events/event.json    # Invoke a single function
sam local generate-event apigateway http-api-proxy    # Generate test events
```

### Testing
```bash
pytest                             # All tests
pytest tests/unit/ -x -v           # Unit tests, stop on first failure
pytest tests/integration/ -v       # Integration tests (requires deployed stack)
INTEGRATION_TEST=1 API_BASE_URL="https://..." pytest tests/integration/
```

## Project Structure

```
.
├── template.yaml              # SAM template (API Gateway + Lambda + DynamoDB)
├── samconfig.toml             # Deploy configuration per environment
├── src/
│   ├── handlers/              # One handler per API endpoint
│   │   ├── create_order.py
│   │   ├── get_order.py
│   │   ├── list_orders.py
│   │   └── health.py
│   ├── models/                # @dataclass models with to/from_dynamodb_item()
│   ├── services/              # Business logic (called by handlers)
│   └── utils/                 # Logging setup, pagination helpers, validators
├── tests/
│   ├── unit/                  # pytest + moto
│   ├── integration/           # Tests against deployed API
│   └── conftest.py            # Fixtures: DynamoDB tables, API event builders
├── events/                    # Sample API Gateway event payloads
└── scripts/
    └── seed.sh                # Seed initial data after deploy
```

## API Handler Pattern

Each handler maps to one HTTP method + resource path. Keep handlers thin.

```python
import json
import logging
import os

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

def lambda_handler(event, context):
    logger.debug("Event: %s", json.dumps(event))
    try:
        result = some_service.process(event)
        return {"statusCode": 200, "body": json.dumps(result)}
    except ValueError as e:
        return {"statusCode": 400, "body": json.dumps({"error": {"code": "BAD_REQUEST", "message": str(e)}})}
    except Exception:
        logger.exception("Unhandled error")
        return {"statusCode": 500, "body": json.dumps({"error": {"code": "INTERNAL_ERROR", "message": "Internal server error"}})}
```

## API Design Rules

- Resource names: plural nouns (`/items`, `/users`), not verbs.
- Pagination: cursor-based with `next_token` query parameter. Response: `{"items": [...], "next_token": "..."}`.
- Error responses: `{"error": {"code": "NOT_FOUND", "message": "..."}}`.
- Default page size 20, max 100. Accept `limit` query parameter.

## DynamoDB Patterns

- `ExpressionAttributeNames` with `#placeholder` for reserved words (`status`, `name`, `type`, `data`, etc.).
- Conditional writes for idempotency.
- Always paginate: loop until `LastEvaluatedKey` is absent.
- TTL: Unix epoch integer for automatic cleanup.

## Key Pitfalls

- `sam build` needs exact Python version. Use `--use-container` if mismatch.
- HTTP API v2 has a hard 30-second integration timeout. Use SQS/EventBridge for long operations.
- Never reference `ServerlessHttpApi` in Lambda env vars (circular dependency).
- First deploy may fail (KMS race). Delete stack and redeploy.
<!-- claude-hub:fragment:end — Add your project-specific content below this line. -->

# Order Service

## Architecture

Single-table DynamoDB design with the following access patterns:

| Access Pattern | Key Condition | Index |
|---|---|---|
| Get order by ID | `pk = ORDER#<id>` | Table |
| List orders by customer | `gsi1pk = CUSTOMER#<id>` | gsi1 |

## API Endpoints

| Method | Path | Handler | Description |
|--------|------|---------|-------------|
| POST | `/v1/orders` | create_order | Create a new order |
| GET | `/v1/orders/{orderId}` | get_order | Get order by ID |
| GET | `/v1/orders?customer_id=X` | list_orders | List orders for a customer |
| PATCH | `/v1/orders/{orderId}/status` | update_order_status | Update order status |
| GET | `/health` | health | Health check |

## Order Status Flow

```
PENDING -> CONFIRMED -> SHIPPED -> DELIVERED
    \
     \-> CANCELLED
```
