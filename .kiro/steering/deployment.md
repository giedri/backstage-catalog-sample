# Deployment Guide

## AWS SAM Workflow

### Build
```bash
sam build                          # Build all functions and layers
sam build --use-container          # Build in Docker (ensures correct Python 3.12)
sam validate --lint                # Validate template.yaml syntax
```

### Deploy
```bash
sam deploy                         # Deploy using samconfig.toml (default environment)
sam deploy --config-env staging    # Deploy to staging
sam deploy --config-env prod       # Deploy to production (requires changeset confirmation)
sam deploy --guided                # Interactive first-time deploy
```

### Teardown
```bash
sam delete                         # Remove the CloudFormation stack
```

## Environments (samconfig.toml)

| Environment | Stack Name | Auto-confirm | Region |
|-------------|-----------|--------------|--------|
| default | `{service-name}` | Yes | us-east-1 |
| staging | `{service-name}-staging` | Yes | us-east-1 |
| prod | `{service-name}-prod` | No (requires review) | us-east-1 |

## Local Development

```bash
sam local start-api                                   # Start local API Gateway on port 3000
sam local invoke FunctionName -e events/event.json    # Invoke a single function
sam local generate-event apigateway http-api-proxy    # Generate test events
```

Sample events are stored in the `events/` directory for each endpoint.

## Deploy Pipeline (Recommended Order)

1. `sam validate --lint` — Validate template
2. `sam build` — Build Lambda packages
3. `pytest tests/unit/ -x -q` — Gate on unit tests passing
4. `sam deploy` — Deploy to target environment
5. Verify health endpoint: `curl https://<api-url>/health`
6. (Optional) Run integration tests: `INTEGRATION_TEST=1 API_BASE_URL=... pytest tests/integration/`
7. (Optional) Seed data: `./scripts/seed.sh`

## SAM Template Structure (template.yaml)

The SAM template defines:
- **Globals** — Shared function config (runtime, memory, timeout, env vars, architecture)
- **DynamoDB Table** — Single-table with GSI, PAY_PER_REQUEST billing, PITR enabled
- **Lambda Functions** — One per endpoint with DynamoDBCrudPolicy
- **HttpApi Events** — Route mapping (method + path → function)
- **Outputs** — API URL, table name, table ARN

### Key Configuration
| Setting | Value | Notes |
|---------|-------|-------|
| Runtime | python3.12 | All functions |
| Architecture | arm64 | Cost/performance optimized |
| Memory | 256 MB | Default for all functions |
| Timeout | 30 seconds | HTTP API hard limit |
| Billing | PAY_PER_REQUEST | No capacity provisioning needed |

## Known Pitfalls

- `sam build` needs matching Python version — use `--use-container` if local Python differs
- HTTP API v2 has a **hard 30-second integration timeout** — use SQS/EventBridge for long operations
- Never reference `ServerlessHttpApi` in Lambda env vars (causes circular dependency)
- First deploy may fail due to KMS race condition — delete stack and redeploy
- `confirm_changeset = true` in prod — always review changes before applying

## Post-Deploy

After deployment, the SAM outputs provide:
- `ApiUrl` — The API Gateway base URL
- `OrderTableName` — DynamoDB table name
- `OrderTableArn` — Table ARN for cross-service access

Use `scripts/seed.sh` to populate initial data if needed.
