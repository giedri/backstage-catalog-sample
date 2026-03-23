#!/usr/bin/env bash
# Seed initial data after deploying the stack.
# Usage: bash scripts/seed.sh [STACK_NAME]

set -euo pipefail

STACK_NAME="${1:-${{ values.name }}}"

API_URL=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' --output text)

echo "API URL: $API_URL"
echo "---"

# Health check
echo "Health check..."
curl -sf "$API_URL/health" | python3 -m json.tool
echo ""

# Create sample items
echo "Creating sample items..."
for i in 1 2 3; do
  ITEM=$(curl -sf -X POST "$API_URL/v1/items" \
    -H "Content-Type: application/json" \
    -d "{
      \"name\": \"Sample Item $i\",
      \"description\": \"Auto-seeded item $i\",
      \"owner_id\": \"OWNER-001\"
    }")
  ITEM_ID=$(echo "$ITEM" | python3 -c "import sys,json; print(json.load(sys.stdin)['item_id'])")
  echo "  Created item: $ITEM_ID"
done

echo ""
echo "Listing items for OWNER-001..."
curl -sf "$API_URL/v1/items?owner_id=OWNER-001" | python3 -m json.tool

echo ""
echo "Seed complete."
