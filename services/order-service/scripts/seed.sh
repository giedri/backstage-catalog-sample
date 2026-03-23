#!/usr/bin/env bash
# Seed initial data after deploying the order-service stack.
# Usage: bash scripts/seed.sh [STACK_NAME]

set -euo pipefail

STACK_NAME="${1:-order-service}"

API_URL=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' --output text)

echo "API URL: $API_URL"
echo "---"

# Health check
echo "Health check..."
curl -sf "$API_URL/health" | python3 -m json.tool
echo ""

# Create sample orders
echo "Creating sample orders..."
for i in 1 2 3; do
  ORDER=$(curl -sf -X POST "$API_URL/v1/orders" \
    -H "Content-Type: application/json" \
    -d "{
      \"customer_id\": \"CUST-001\",
      \"items\": [
        {\"product_id\": \"PROD-00$i\", \"product_name\": \"Sample Product $i\", \"quantity\": $i, \"unit_price\": 9.99}
      ]
    }")
  ORDER_ID=$(echo "$ORDER" | python3 -c "import sys,json; print(json.load(sys.stdin)['order_id'])")
  echo "  Created order: $ORDER_ID"
done

echo ""
echo "Listing orders for CUST-001..."
curl -sf "$API_URL/v1/orders?customer_id=CUST-001" | python3 -m json.tool

echo ""
echo "Seed complete."
