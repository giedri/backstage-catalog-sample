# Project Overview

## Purpose

This repository is ACME's **Backstage software template and sample services** for their serverless microservice platform. It contains:

1. **Backstage Software Template** (`template/`) — A scaffolder definition registered in Backstage that enables developers to self-service create new serverless microservices from the Backstage portal.
2. **Sample Implementation** (`services/order-service/`) — A fully-implemented Order Management microservice demonstrating the patterns the template produces.

## Repository Structure

```
.
├── template/                      # Backstage software template
│   ├── template.yaml              #   Scaffolder definition (registered in Backstage)
│   └── skeleton/                  #   Nunjucks-templated project skeleton
│       ├── catalog-info.yaml      #     Backstage entities (uses ${{ values.* }} placeholders)
│       ├── template.yaml          #     SAM template (parameterized)
│       ├── src/                   #     Generic CRUD handlers, model, service, utils
│       ├── tests/                 #     pytest + moto unit test scaffolding
│       ├── docs/                  #     OpenAPI spec + DynamoDB access patterns
│       ├── events/                #     Sample payloads for sam local invoke
│       ├── scripts/               #     Post-deploy seed script
│       └── .claude/               #     Claude Code config (from fragment system)
│
└── services/                      # Concrete service implementations
    └── order-service/             #   Order management microservice
        ├── catalog-info.yaml      #     4 Backstage entities (Component, API, Resource, System)
        ├── CLAUDE.md              #     Claude Code toolchain reference + project context
        ├── .claude/               #     Claude Code settings and skills
        ├── template.yaml          #     SAM infrastructure definition
        ├── samconfig.toml         #     Deploy config (default, staging, prod)
        ├── src/
        │   ├── handlers/          #     One Lambda handler per API endpoint
        │   ├── models/            #     @dataclass models with DynamoDB serialization
        │   ├── services/          #     Business logic layer
        │   └── utils/             #     Response helpers, shared utilities
        ├── tests/
        │   ├── unit/              #     pytest + moto
        │   ├── integration/       #     Against deployed API (env var gated)
        │   └── conftest.py        #     Fixtures: DynamoDB tables, API event builders
        ├── docs/                  #     OpenAPI spec + access pattern docs
        ├── events/                #     Sample API Gateway event payloads
        └── scripts/               #     Seed script
```

## Architecture

**Pattern:** Serverless CRUD microservice  
**Flow:** AWS API Gateway (HTTP API v2) → AWS Lambda → Amazon DynamoDB

Each service uses:
- **Single-table DynamoDB design** with composite keys (`pk`/`sk`) and GSI for alternate access patterns
- **Thin Lambda handlers** — one function per HTTP method + resource path
- **Service layer** — business logic isolated from event parsing
- **Dataclass models** — with DynamoDB and API serialization methods

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.12 |
| Runtime | AWS Lambda (arm64) |
| API | AWS API Gateway HTTP API v2 |
| Database | Amazon DynamoDB (PAY_PER_REQUEST, single-table) |
| IaC | AWS SAM / CloudFormation |
| Developer Portal | Backstage (scaffolder v1beta3) |
| Testing | pytest, moto (AWS mocking) |
| Deploy Config | samconfig.toml (default, staging, prod) |

## Backstage Integration

Every service registers **4 entity types** in `catalog-info.yaml`:
- **Component** — The service itself (type: service)
- **API** — REST API definition (linked to OpenAPI spec via `$text: ./docs/openapi.yaml`)
- **Resource** — DynamoDB table (type: database)
- **System** — Domain grouping

Required annotations: `github.com/project-slug`, `backstage.io/techdocs-ref`, `aws.amazon.com/region`, `pagerduty.com/service-id`

## Key Files Reference

| File | Purpose |
|------|---------|
| `template.yaml` | SAM infrastructure definition (Lambda + API Gateway + DynamoDB) |
| `samconfig.toml` | Environment-specific deploy parameters |
| `catalog-info.yaml` | Backstage entity registration |
| `docs/openapi.yaml` | OpenAPI 3.0 API specification |
| `docs/access-patterns.md` | DynamoDB key schema and access patterns |
| `CLAUDE.md` | Claude Code toolchain reference |
