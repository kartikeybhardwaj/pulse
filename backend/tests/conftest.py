"""Shared test fixtures — mocked DynamoDB table matching the CDK schema."""

import pytest
import boto3
from moto import mock_aws


@pytest.fixture(autouse=True)
def aws_env(monkeypatch):
    monkeypatch.setenv("TABLE_NAME", "Pulse")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("JWT_SECRET_PARAM", "/pulse/jwt-secret")
    monkeypatch.setenv("SES_FROM_EMAIL", "test@example.com")
    monkeypatch.setenv("WS_API_ENDPOINT", "")

    with mock_aws():
        # Create DynamoDB table
        client = boto3.client("dynamodb", region_name="us-east-1")
        client.create_table(
            TableName="Pulse",
            KeySchema=[
                {"AttributeName": "PK", "KeyType": "HASH"},
                {"AttributeName": "SK", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"},
                {"AttributeName": "GSI1PK", "AttributeType": "S"},
                {"AttributeName": "GSI1SK", "AttributeType": "S"},
                {"AttributeName": "GSI2PK", "AttributeType": "S"},
                {"AttributeName": "GSI2SK", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "GSI1",
                    "KeySchema": [
                        {"AttributeName": "GSI1PK", "KeyType": "HASH"},
                        {"AttributeName": "GSI1SK", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
                {
                    "IndexName": "GSI2",
                    "KeySchema": [
                        {"AttributeName": "GSI2PK", "KeyType": "HASH"},
                        {"AttributeName": "GSI2SK", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        # SSM parameter for JWT
        boto3.client("ssm", region_name="us-east-1").put_parameter(
            Name="/pulse/jwt-secret", Value="test-secret-key-for-jwt", Type="String"
        )

        # SES verified sender (moto sandbox requires it)
        boto3.client("ses", region_name="us-east-1").verify_email_identity(EmailAddress="test@example.com")

        # Reset all lazy singletons so they pick up the mock
        from lib.db import reset_table

        reset_table()

        import lib.auth_service

        lib.auth_service.TOKEN_SECRET = None
        lib.auth_service._ses = None
        lib.auth_service._ssm = None

        # Ensure Decimal encoder is active
        import lib.response  # noqa: F401

        yield

        reset_table()
        lib.auth_service.TOKEN_SECRET = None
        lib.auth_service._ses = None
        lib.auth_service._ssm = None
