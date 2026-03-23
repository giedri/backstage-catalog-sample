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
│   │   ├── create_item.py
│   │   ├── get_item.py
│   │   ├── list_items.py
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
from src.services.item_service import ItemService

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

service = ItemService(table_name=os.environ["TABLE_NAME"])

def lambda_handler(event, context):
    logger.debug("Event: %s", json.dumps(event))
    try:
        item_id = event["pathParameters"]["itemId"]
        item = service.get_item(item_id)
        if not item:
            return {"statusCode": 404, "body": json.dumps({"error": {"code": "NOT_FOUND", "message": "Item not found"}})}
        return {"statusCode": 200, "body": json.dumps(item)}
    except KeyError as e:
        logger.warning("Missing parameter: %s", e)
        return {"statusCode": 400, "body": json.dumps({"error": {"code": "BAD_REQUEST", "message": f"Missing: {e}"}})}
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
- Conditional writes: `ConditionExpression="attribute_not_exists(pk)"`.
- Always paginate: loop until `LastEvaluatedKey` is absent.
- TTL: Unix epoch integer, not ISO string.
- Atomic counters: `UpdateExpression="ADD #count :inc"`.

## SAM Template Rules

- Use `AWS::StackName` for all dynamic naming. Pass as `STACK_NAME` env var.
- SSM parameters scoped to stack: `!Sub "/${AWS::StackName}/param"`.
- Use `HttpApi` events (API Gateway v2). Do not mix with `Api` (v1).
- Never reference `ServerlessHttpApi` in env vars (circular dependency).
- Never use `SSMParameterReadPolicy` with `/`-prefixed names. Use direct IAM Statement.
- HTTP API v2: 30-second hard timeout. Use SQS/EventBridge for long operations.

## Testing

- `mock_aws` context manager for all AWS mocking.
- DynamoDB table fixtures must match `template.yaml` exactly (GSIs, key schemas, attributes).
- `make_api_event()` helper in `conftest.py`.
- Hypothesis for property-based testing of model serialization.
- Integration tests gated by `INTEGRATION_TEST=1` env var.

## Key Pitfalls

- `sam build` needs exact Python version. Use `--use-container` if mismatch.
- Layer `BuildMethod` adds `python/` prefix. Don't nest source under `python/`.
- First deploy may fail (KMS race). Delete stack and redeploy.
- `!Sub` cannot be a Parameter default. Inline it in env vars and IAM resources.
<!-- claude-hub:fragment:end — Add your project-specific content below this line. -->

# Project Notes

<!-- Add project-specific guidance: API documentation, access patterns, architecture decisions. -->
