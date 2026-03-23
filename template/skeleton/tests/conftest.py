import json
import os

import boto3
import pytest
from moto import mock_aws

os.environ["TABLE_NAME"] = "test-items"
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
            TableName="test-items",
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
def item_service(dynamodb_table):
    """ItemService wired to the mocked DynamoDB table."""
    from src.services.item_service import ItemService

    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    return ItemService(table_name="test-items", dynamodb_resource=dynamodb)


def make_api_event(
    method: str = "GET",
    path: str = "/",
    body: dict | None = None,
    path_parameters: dict | None = None,
    query_string_parameters: dict | None = None,
) -> dict:
    """Build an API Gateway HTTP API v2 proxy event."""
    return {
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
