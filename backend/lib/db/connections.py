"""WebSocket connection database operations.

Connection tracking:
  PK=CONN#<connId> SK=META — tracks active WebSocket connections

Subscription tracking:
  PK=SUB#<pollId> SK=CONN#<connId> — links a connection to a poll for broadcast
"""

from lib.db import table


def put_connection(conn_id: str, connected_at: int) -> None:
    table.put_item(Item={"PK": f"CONN#{conn_id}", "SK": "META", "connectedAt": connected_at})


def delete_connection(conn_id: str) -> None:
    """Remove connection and all its poll subscriptions."""
    table.delete_item(Key={"PK": f"CONN#{conn_id}", "SK": "META"})
    # Scan for all SUB#* items referencing this connection — not ideal at scale
    # but acceptable since each user has very few active subscriptions
    r = table.scan(
        FilterExpression="contains(SK, :conn)",
        ExpressionAttributeValues={":conn": f"CONN#{conn_id}"},
    )
    for item in r.get("Items", []):
        table.delete_item(Key={"PK": item["PK"], "SK": item["SK"]})


def put_subscription(poll_id: str, conn_id: str, subscribed_at: int) -> None:
    table.put_item(Item={"PK": f"SUB#{poll_id}", "SK": f"CONN#{conn_id}", "subscribedAt": subscribed_at})


def get_subscriptions(poll_id: str) -> list[dict]:
    """Get all WebSocket connections subscribed to a poll (for broadcast)."""
    r = table.query(
        KeyConditionExpression="PK = :pk AND begins_with(SK, :sk)",
        ExpressionAttributeValues={":pk": f"SUB#{poll_id}", ":sk": "CONN#"},
    )
    return r.get("Items", [])


def delete_subscription(poll_id: str, conn_id: str) -> None:
    """Remove a stale subscription (called when broadcast gets GoneException)."""
    table.delete_item(Key={"PK": f"SUB#{poll_id}", "SK": f"CONN#{conn_id}"})
