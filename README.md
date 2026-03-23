# ACME Backstage Catalog

Backstage software template and sample services for ACME's serverless microservice platform.

## Repository structure

```
.
├── template/                      # Backstage software template
│   ├── template.yaml              #   Scaffolder definition (registered in Backstage)
│   └── skeleton/                  #   Project skeleton rendered for each new service
│       ├── catalog-info.yaml      #     Backstage entities (Component, API, Resource, System)
│       ├── template.yaml          #     SAM template (API Gateway + Lambda + DynamoDB)
│       ├── samconfig.toml         #     Deploy config (default, staging, prod)
│       ├── src/                   #     Generic CRUD handlers, model, service, utils
│       ├── tests/                 #     pytest + moto unit tests
│       ├── docs/                  #     OpenAPI spec + DynamoDB access patterns
│       ├── events/                #     Sample payloads for sam local invoke
│       └── scripts/               #     Post-deploy seed script
│
└── services/                      # Sample service implementations
    └── order-service/             #   Order management microservice
        ├── catalog-info.yaml      #     Backstage entities
        ├── CLAUDE.md              #     Claude Code config (from sam-api fragment)
        ├── .claude/               #     Claude Code settings and skills
        ├── template.yaml          #     SAM template
        ├── src/                   #     Order handlers, model, service
        ├── tests/                 #     Unit tests
        ├── docs/                  #     OpenAPI spec + access patterns
        └── scripts/               #     Seed script
```

## Backstage template

`template/template.yaml` is the scaffolder definition. Register it in Backstage to let developers create new serverless microservices from the portal.

The template:
1. Scaffolds a working CRUD service from `template/skeleton/` with Nunjucks placeholders
2. Copies Claude Code configuration from the [claude-hub](https://github.com/acme-org/claude-hub) `sam-api` fragment
3. Publishes to GitHub
4. Registers the component in the Backstage catalog

### Parameters

| Parameter | Description |
|-----------|-------------|
| `name` | Service name (stack name, repo name, lowercase with hyphens) |
| `description` | Brief description |
| `owner` | Owning team (Backstage group) |
| `region` | AWS region |
| `repoUrl` | GitHub repository location |

## Sample: order-service

`services/order-service/` is a fully implemented example of what the template produces, customized for order management. It demonstrates:

- 5 API endpoints (create, get, list, update status, health)
- Single-table DynamoDB design with GSI for customer queries
- Cursor-based pagination
- Idempotent writes with conditional expressions
- Unit tests with moto and pytest
- OpenAPI 3.0 spec
- Claude Code configuration with `sam-deploy` and `api-test` skills

Use it as a reference when building new services from the template.
