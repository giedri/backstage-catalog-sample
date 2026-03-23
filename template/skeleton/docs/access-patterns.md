# DynamoDB Access Patterns

## Table: ${{ values.name }}-items

Single-table design using `pk`/`sk` primary key with one GSI.

### Key Schema

| Key | Format | Example |
|-----|--------|---------|
| `pk` | `ITEM#<item_id>` | `ITEM#550e8400-e29b-41d4-a716-446655440000` |
| `sk` | `ITEM#<item_id>` | `ITEM#550e8400-e29b-41d4-a716-446655440000` |
| `gsi1pk` | `OWNER#<owner_id>` | `OWNER#OWNER-001` |
| `gsi1sk` | `ITEM#<created_at>` | `ITEM#2026-03-23T10:00:00+00:00` |

### Access Patterns

| # | Pattern | Index | Key Condition | Notes |
|---|---------|-------|---------------|-------|
| 1 | Get item by ID | Table | `pk = ITEM#<id> AND sk = ITEM#<id>` | Direct lookup |
| 2 | List items by owner (newest first) | gsi1 | `gsi1pk = OWNER#<id>` | `ScanIndexForward=False`, paginated |

### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `item_id` | S | UUID |
| `item_name` | S | Name (stored as `item_name` to avoid DynamoDB reserved word `name`) |
| `description` | S | Description |
| `owner_id` | S | Owner identifier |
| `created_at` | S | ISO 8601 timestamp |
| `updated_at` | S | ISO 8601 timestamp |
| `ttl` | N | Unix epoch (reserved for future cleanup) |
