# API Test

Generates or runs integration tests against the deployed API.

## Steps

1. **Get the API base URL**
   ```bash
   API_URL=$(aws cloudformation describe-stacks \
     --stack-name $(grep stack_name samconfig.toml | head -1 | awk -F'"' '{print $2}') \
     --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' --output text)
   echo "API URL: $API_URL"
   ```

2. **Run integration tests**
   ```bash
   INTEGRATION_TEST=1 API_BASE_URL="$API_URL" pytest tests/integration/ -v
   ```

3. **If no integration tests exist**, generate them based on the SAM template:
   - Read `template.yaml` to find all API Gateway event sources.
   - For each endpoint, create a test in `tests/integration/` that:
     - Sends a request with valid input and asserts 200/201.
     - Sends a request with invalid input and asserts 400.
     - Sends a request for a nonexistent resource and asserts 404.
   - Use `httpx` with `follow_redirects=True` for HTTP calls.
   - Read API key from environment variable `API_KEY` if auth is configured.

## Output

Report which endpoints were tested and their results. Flag any failures with the response body for debugging.
