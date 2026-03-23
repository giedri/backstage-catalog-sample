# DynamoDB Access Patterns

## Table: order-service-orders

Single-table design using `pk`/`sk` primary key with one GSI.

### Key Schema

| Key | Format | Example |
|-----|--------|---------|
| `pk` | `ORDER#<order_id>` | `ORDER#550e8400-e29b-41d4-a716-446655440000` |
| `sk` | `ORDER#<order_id>` | `ORDER#550e8400-e29b-41d4-a716-446655440000` |
| `gsi1pk` | `CUSTOMER#<customer_id>` | `CUSTOMER#CUST-001` |
| `gsi1sk` | `ORDER#<created_at>` | `ORDER#2026-03-23T10:00:00+00:00` |

### Access Patterns

| # | Pattern | Index | Key Condition | Notes |
|---|---------|-------|---------------|-------|
| 1 | Get order by ID | Table | `pk = ORDER#<id> AND sk = ORDER#<id>` | Direct lookup |
| 2 | List orders by customer (newest first) | gsi1 | `gsi1pk = CUSTOMER#<id>` | `ScanIndexForward=False`, paginated |

### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `order_id` | S | UUID |
| `customer_id` | S | Customer identifier |
| `order_status` | S | PENDING, CONFIRMED, SHIPPED, DELIVERED, CANCELLED |
| `items` | L | List of order item maps |
| `total_amount` | S | Stored as string for decimal precision |
| `created_at` | S | ISO 8601 timestamp |
| `updated_at` | S | ISO 8601 timestamp |
| `ttl` | N | Unix epoch (not currently used, reserved for future cleanup) |
