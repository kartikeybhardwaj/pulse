"""WebSocket broadcast — sends poll updates to all subscribed connections.

When a vote, edit, close, or delete happens, the REST handler calls
broadcast_poll_update() to push the new state to all clients viewing that poll.

Uses the API Gateway Management API to post to each WebSocket connection.
Stale connections (GoneException) are cleaned up automatically.
"""

import json
import os

import boto3

from lib.db.connections import get_subscriptions, delete_subscription

WS_API_ENDPOINT = os.environ.get("WS_API_ENDPOINT", "")


def broadcast_poll_update(poll_id: str, payload: dict) -> None:
    """Send payload to all WebSocket connections subscribed to this poll."""
    if not WS_API_ENDPOINT:
        return  # WS not configured (e.g., local dev)
    apigw = boto3.client("apigatewaymanagementapi", endpoint_url=WS_API_ENDPOINT)
    data = json.dumps(payload).encode()
    for item in get_subscriptions(poll_id):
        conn_id = item["SK"].split("#", 1)[1]  # SUB#<pollId> / CONN#<connId>
        try:
            apigw.post_to_connection(ConnectionId=conn_id, Data=data)
        except apigw.exceptions.GoneException:
            # Client disconnected — clean up stale subscription
            delete_subscription(poll_id, conn_id)
        except Exception:
            pass  # Non-critical — don't fail the request if one broadcast fails
