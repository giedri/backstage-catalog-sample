import json
import os

import boto3
import pytest
from moto import mock_aws

os.environ["TABLE_NAME"] = "test-orders"
os.environ["LOG_LEVEL"] = "DEBUG"
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
os.environ["AWS_ACCESS_KEY_ID"] = "testing"
os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"


@pytest.fixture
def aws_credentials():
    """Mocked AWS credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


@pytest.fixture
def dynamodb_table(aws_credentials):
    """Create a mocked DynamoDB table matching template.yaml."""
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        table = dynamodb.create_table(
            TableName="test-orders",
            KeySchema=[
                {"AttributeName": "pk", "KeyType": "HASH"},
                {"AttributeName": "sk", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "pk", "AttributeType": "S"},
                {"AttributeName": "sk", "AttributeType": "S"},
                {"AttributeName": "gsi1pk", "AttributeType": "S"},
                {"AttributeName": "gsi1sk", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "gsi1",
                    "KeySchema": [
                        {"AttributeName": "gsi1pk", "KeyType": "HASH"},
                        {"AttributeName": "gsi1sk", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        yield table


@pytest.fixture
def order_service(dynamodb_table):
    """OrderService wired to the mocked DynamoDB table."""
    from src.services.order_service import OrderService

    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    return OrderService(table_name="test-orders", dynamodb_resource=dynamodb)


_NO_AUTH = object()


def make_api_event(
    method: str = "GET",
    path: str = "/",
    body: dict | None = None,
    path_parameters: dict | None = None,
    query_string_parameters: dict | None = None,
    claims: dict | object | None = None,
) -> dict:
    """Build an API Gateway HTTP API v2 proxy event.

    Args:
        claims: JWT claims dict to include in authorizer context.
                Defaults to {'sub': 'CUST-001', 'cognito:groups': ''} for backward
                compatibility with Cognito auth.
                Pass _NO_AUTH to simulate a request with no authorizer context.
    """
    if claims is None:
        claims = {"sub": "CUST-001", "cognito:groups": ""}

    event = {
        "version": "2.0",
        "requestContext": {
            "http": {
                "method": method,
                "path": path,
            },
            "requestId": "test-request-id",
        },
        "headers": {"content-type": "application/json"},
        "body": json.dumps(body) if body else None,
        "pathParameters": path_parameters,
        "queryStringParameters": query_string_parameters,
        "isBase64Encoded": False,
    }

    if claims is not _NO_AUTH:
        event["requestContext"]["authorizer"] = {"jwt": {"claims": claims}}

    return event
