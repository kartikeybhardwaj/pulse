"""WebSocket subscribe handler."""

import json

from lib.db.connections import put_subscription
from lib.utils import now_ts


def handler(event, context):
    conn_id = event["requestContext"]["connectionId"]
    body = json.loads(event.get("body", "{}"))
    poll_id = body.get("pollId", "")
    if not poll_id:
        return {"statusCode": 400}
    put_subscription(poll_id, conn_id, now_ts())
    return {"statusCode": 200}
