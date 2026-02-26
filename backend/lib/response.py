"""HTTP response builder and Decimal-safe JSON encoding.

DynamoDB returns all numbers as Decimal objects. Python's json.dumps can't
serialize Decimal by default. We override the global JSONEncoder so every
json.dumps call in the Lambda process handles Decimals automatically —
including calls inside boto3 and broadcast.py.
"""

import json
from decimal import Decimal


class _DecimalEncoder(json.JSONEncoder):
    """JSON encoder that converts Decimal → int/float."""

    def default(self, o):
        if isinstance(o, Decimal):
            return int(o) if o == int(o) else float(o)
        return super().default(o)


# Monkey-patch the global encoder — any module that imports json will use this
json.JSONEncoder = _DecimalEncoder
# Also replace the cached default encoder instance used by json.dumps()
json._default_encoder = _DecimalEncoder()


def response(status: int, body: dict | list | None = None) -> dict:
    """Build an API Gateway Lambda proxy response."""
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Credentials": "true",
        },
        "body": json.dumps(body) if body else "",
    }
