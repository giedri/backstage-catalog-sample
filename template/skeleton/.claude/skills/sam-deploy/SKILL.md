# SAM Deploy

Deploys the SAM API service to AWS. Runs build, validation, and deploy steps in sequence.

## Steps

1. **Validate the template**
   ```bash
   sam validate --lint
   ```
   Fix any validation errors before proceeding.

2. **Check for YAML issues**
   ```bash
   python3 -c "import yaml; yaml.safe_load(open('template.yaml'))"
   ```

3. **Build the application**
   ```bash
   sam build
   ```
   If the build fails due to Python version mismatch:
   ```bash
   sam build --use-container
   ```

4. **Run tests before deploying**
   ```bash
   pytest tests/unit/ -x -q
   ```
   Do not deploy if tests fail.

5. **Deploy**
   ```bash
   sam deploy
   ```

6. **Verify API endpoints**
   Extract the API URL from stack outputs and test a health endpoint:
   ```bash
   API_URL=$(aws cloudformation describe-stacks \
     --stack-name $(grep stack_name samconfig.toml | head -1 | awk -F'"' '{print $2}') \
     --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' --output text)
   curl -s "$API_URL/health" | python3 -m json.tool
   ```

## Troubleshooting

- **First deploy KMS/CreateGrant failure**: `sam delete` then redeploy.
- **30-second timeout on HTTP API**: Move long operations to async (SQS trigger).
- **Multiple GSI changes**: Delete stack and redeploy.
