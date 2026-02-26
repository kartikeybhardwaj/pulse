"""DynamoDB table connection — lazy initialization for testability."""

import os
import boto3

TABLE_NAME = os.environ.get("TABLE_NAME", "Pulse")

_table = None


def _get_table():
    global _table
    if _table is None:
        ddb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))
        _table = ddb.Table(TABLE_NAME)
    return _table


class _TableProxy:
    """Proxy that lazily initializes the DynamoDB table on first access.
    This allows moto to mock the table before any real connection is made."""

    def __getattr__(self, name):
        return getattr(_get_table(), name)


table = _TableProxy()


def reset_table():
    """Force re-initialization — used by tests after mocking."""
    global _table
    _table = None
