"""Pulse CDK Stack — composes all infrastructure resources into a single CloudFormation stack.

Resources:
  - Database: DynamoDB single-table with GSIs
  - RestApi: API Gateway + Lambda for auth and poll CRUD
  - WebSocketApi: API Gateway WebSocket + Lambda for real-time updates
  - Frontend: S3 + CloudFront for SvelteKit SPA

All Lambda functions share the same code bundle (backend/) and common config.
"""

import os

from aws_cdk import Stack, Duration, CfnOutput, aws_lambda as _lambda
from constructs import Construct

from resources.database import Database
from resources.rest_api import RestApi
from resources.websocket_api import WebSocketApi
from resources.frontend import Frontend


class PulseStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        backend_dir = os.path.join(os.path.dirname(__file__), "..", "backend")

        db = Database(self, "Database")

        # Shared across all Lambdas — table name injected via env var
        common_env = {
            "TABLE_NAME": db.table.table_name,
            "POWERTOOLS_SERVICE_NAME": "pulse",
            "LOG_LEVEL": "INFO",
        }
        common_lambda_props = dict(
            runtime=_lambda.Runtime.PYTHON_3_12,
            memory_size=256,
            timeout=Duration.seconds(10),
            environment=common_env,
        )

        rest = RestApi(self, "RestApi", table=db.table, backend_dir=backend_dir, common_lambda_props=common_lambda_props, common_env=common_env)
        ws = WebSocketApi(self, "WebSocketApi", table=db.table, rest_fn=rest.rest_fn, backend_dir=backend_dir, common_lambda_props=common_lambda_props)
        fe = Frontend(self, "Frontend", rest_api=rest.api)

        # CDK outputs — used for frontend build (VITE_WS_URL) and verification
        CfnOutput(self, "RestApiUrl", value=rest.api.url)
        CfnOutput(self, "WsApiUrl", value=ws.stage.url)
        CfnOutput(self, "DistributionUrl", value=f"https://{fe.distribution.distribution_domain_name}")
        CfnOutput(self, "TableName", value=db.table.table_name)
