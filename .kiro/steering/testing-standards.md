# Testing Standards

## Framework & Dependencies

- **pytest** >= 8.0 — test runner
- **moto** >= 5.0 — AWS service mocking (DynamoDB)
- **hypothesis** >= 6.0 — property-based testing (available, use when appropriate)
- **boto3-stubs[dynamodb]** — type hints for DynamoDB operations

Install: `pip install -r requirements-dev.txt`

## Test Structure

```
tests/
├── __init__.py
├── conftest.py              # Shared fixtures and helpers
├── unit/                    # Fast, isolated, no network
│   ├── __init__.py
│   ├── test_handlers.py     # Lambda handler tests
│   └── test_order_service.py # Service layer tests
└── integration/             # Against deployed API (env var gated)
```

## Running Tests

```bash
# All tests
pytest

# Unit tests only (fast)
pytest tests/unit/ -x -v

# Integration tests (requires deployed stack)
INTEGRATION_TEST=1 API_BASE_URL="https://..." pytest tests/integration/ -v
```

## Fixtures (conftest.py)

### Environment Setup
Environment variables are set at module level in `conftest.py`:
```python
os.environ["TABLE_NAME"] = "test-orders"
os.environ["LOG_LEVEL"] = "DEBUG"
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
os.environ["AWS_ACCESS_KEY_ID"] = "testing"
os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
```

### Key Fixtures

| Fixture | Scope | Purpose |
|---------|-------|---------|
| `aws_credentials` | function | Sets mocked AWS credentials |
| `dynamodb_table` | function | Creates mocked DynamoDB table matching template.yaml schema |
| `order_service` | function | OrderService wired to mocked DynamoDB |

### Event Builder Helper
```python
def make_api_event(
    method: str = "GET",
    path: str = "/",
    body: dict | None = None,
    path_parameters: dict | None = None,
    query_string_parameters: dict | None = None,
) -> dict:
    """Build an API Gateway HTTP API v2 proxy event."""
```

## Test Patterns

### Service Layer Tests
- Use `@mock_aws` class decorator
- Use `order_service` fixture (already wired to mocked DynamoDB)
- Test happy path, error cases, edge cases, pagination

```python
@mock_aws
class TestOrderService:
    def test_create_order(self, order_service):
        order = order_service.create_order(customer_id="CUST-001", items=SAMPLE_ITEMS)
        assert order.status == OrderStatus.PENDING

    def test_get_order_not_found(self, order_service):
        with pytest.raises(OrderNotFoundError):
            order_service.get_order("nonexistent-id")
```

### Handler Tests
- Use `@mock_aws` class decorator
- Use `dynamodb_table` fixture (handlers instantiate their own service)
- Use `make_api_event()` helper to construct Lambda events
- Assert on `statusCode` and parsed `body`

```python
@mock_aws
class TestCreateOrderHandler:
    def test_create_order_success(self, dynamodb_table):
        from src.handlers.create_order import lambda_handler

        event = make_api_event(
            method="POST",
            path="/v1/orders",
            body={"customer_id": "CUST-001", "items": SAMPLE_ITEMS},
        )
        response = lambda_handler(event, None)
        assert response["statusCode"] == 201
```

### Important Notes
- Import handlers **inside test methods** (they read env vars at import time)
- The `dynamodb_table` fixture yields inside `mock_aws()` context — table exists only during test
- `order_service` fixture creates an `OrderService` with explicit `dynamodb_resource` injection
- DynamoDB table fixture must match the schema in `template.yaml` (pk/sk + GSI)

## What to Test

| Layer | What to Cover |
|-------|--------------|
| Handlers | Input parsing, status codes, error responses, delegation to service |
| Services | Business logic, CRUD operations, pagination, error conditions |
| Models | Serialization round-trips (to/from DynamoDB), computed fields |

## Test Data Conventions

- Customer IDs: `CUST-001`, `CUST-002`, etc.
- Product IDs: `PROD-001`, `PROD-002`, etc.
- Use `pytest.approx()` for floating-point comparisons
- Define `SAMPLE_ITEMS` at module level for reuse
