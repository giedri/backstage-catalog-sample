# API Test

Generates or runs integration tests against the deployed Order API.

## Steps

1. **Get the API base URL**
   ```bash
   API_URL=$(aws cloudformation describe-stacks \
     --stack-name order-service \
     --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' --output text)
   echo "API URL: $API_URL"
   ```

2. **Run integration tests**
   ```bash
   INTEGRATION_TEST=1 API_BASE_URL="$API_URL" pytest tests/integration/ -v
   ```

3. **Quick manual smoke test**
   ```bash
   # Health check
   curl -s "$API_URL/health" | python3 -m json.tool

   # Create an order
   curl -s -X POST "$API_URL/v1/orders" \
     -H "Content-Type: application/json" \
     -d '{"customer_id":"CUST-001","items":[{"product_id":"P1","product_name":"Widget","quantity":2,"unit_price":9.99}]}' \
     | python3 -m json.tool
   ```

## Output

Report which endpoints were tested and their results. Flag any failures with the response body for debugging.
