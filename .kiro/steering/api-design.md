# API Design Standards

## URL Structure

- **Versioned paths**: `/v1/resource`
- **Plural nouns** for resources: `/v1/orders`, `/v1/users` (not verbs)
- **Nested resources** for actions: `/v1/orders/{orderId}/status`
- **Health check**: `/health` (unversioned)

## HTTP Methods

| Method | Use | Example |
|--------|-----|---------|
| POST | Create resource | `POST /v1/orders` |
| GET | Retrieve resource(s) | `GET /v1/orders/{orderId}` |
| PATCH | Partial update | `PATCH /v1/orders/{orderId}/status` |
| DELETE | Remove resource | `DELETE /v1/orders/{orderId}` |

## Request Format

- Content-Type: `application/json`
- Path parameters for resource identifiers: `{orderId}`
- Query parameters for filtering and pagination: `?customer_id=X&limit=20&next_token=...`

## Response Format

### Success Response
```json
{
  "order_id": "uuid",
  "customer_id": "CUST-001",
  "status": "PENDING",
  "items": [...],
  "total_amount": 44.97,
  "created_at": "2026-03-23T10:00:00+00:00",
  "updated_at": "2026-03-23T10:00:00+00:00"
}
```

### List Response (Paginated)
```json
{
  "items": [...],
  "next_token": "base64-encoded-cursor-or-null"
}
```

### Error Response
```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Order not found"
  }
}
```

## Error Codes

| HTTP Status | Code | When |
|-------------|------|------|
| 400 | `BAD_REQUEST` | Missing required fields, invalid input |
| 404 | `NOT_FOUND` | Resource does not exist |
| 409 | `CONFLICT` | Duplicate creation (idempotency check) |
| 500 | `INTERNAL_ERROR` | Unhandled exceptions |

## Pagination

- **Style**: Cursor-based (NOT offset-based)
- **Query param**: `next_token` (opaque base64-encoded string)
- **Default page size**: 20
- **Maximum page size**: 100
- **Limit param**: `limit` query parameter (clamped to max)
- **Response**: Include `next_token` field only when more results exist

## OpenAPI Specification

Every service must have a complete OpenAPI 3.0 spec at `docs/openapi.yaml` containing:
- All endpoints with request/response schemas
- Component schemas for reuse (`$ref`)
- Server URL template for API Gateway
- Contact info linking to Backstage catalog

#[[file:services/order-service/docs/openapi.yaml]]

## Status Codes for Operations

| Operation | Success Code | Notes |
|-----------|-------------|-------|
| Create | 201 | Returns created resource |
| Get | 200 | Returns resource |
| List | 200 | Returns paginated list |
| Update | 200 | Returns updated resource |
| Delete | 204 | No content |
| Health | 200 | Returns status object |
