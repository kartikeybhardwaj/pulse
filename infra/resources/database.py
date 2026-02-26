"""DynamoDB single-table design.

Single table "Pulse" with PK/SK pattern supporting all entity types:
  USER#<username>  / PROFILE       — user accounts
  EMAIL#<email>    / LOOKUP        — email → username mapping
  POLL#<pollId>    / META          — poll metadata
  POLL#<pollId>    / VOTE#<alias>  — individual votes
  CONN#<connId>    / META          — WebSocket connections
  SUB#<pollId>     / CONN#<connId> — WebSocket subscriptions

GSI1: Recent polls listing
  GSI1PK = "POLLS", GSI1SK = "T#<timestamp>" (sorted newest first)

GSI2: Creator's polls listing
  GSI2PK = "CREATOR#<alias>", GSI2SK = "T#<timestamp>"

TTL attribute "ttl" auto-deletes poll data 6 months after creation.
On-demand billing — no provisioned capacity to manage.
"""

from aws_cdk import RemovalPolicy, aws_dynamodb as dynamodb
from constructs import Construct


class Database(Construct):
    def __init__(self, scope: Construct, id: str):
        super().__init__(scope, id)

        self.table = dynamodb.Table(
            self, "PulseTable",
            table_name="Pulse",
            partition_key=dynamodb.Attribute(name="PK", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="SK", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
            time_to_live_attribute="ttl",
        )

        # GSI1: all polls sorted by creation time (for "Recent" page)
        self.table.add_global_secondary_index(
            index_name="GSI1",
            partition_key=dynamodb.Attribute(name="GSI1PK", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="GSI1SK", type=dynamodb.AttributeType.STRING),
            projection_type=dynamodb.ProjectionType.ALL,
        )

        # GSI2: polls by creator (for "My Polls" page — no in-memory filtering)
        self.table.add_global_secondary_index(
            index_name="GSI2",
            partition_key=dynamodb.Attribute(name="GSI2PK", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="GSI2SK", type=dynamodb.AttributeType.STRING),
            projection_type=dynamodb.ProjectionType.ALL,
        )
