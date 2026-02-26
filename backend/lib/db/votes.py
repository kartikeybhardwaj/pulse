"""Vote database operations."""

from lib.db import table
from lib.models.vote import Vote


def get_votes(poll_id: str) -> list[Vote]:
    r = table.query(
        KeyConditionExpression="PK = :pk AND begins_with(SK, :sk)",
        ExpressionAttributeValues={":pk": f"POLL#{poll_id}", ":sk": "VOTE#"},
    )
    return [Vote.from_db(item) for item in r.get("Items", [])]


def get_user_vote(poll_id: str, alias: str) -> str | None:
    if alias == "anonymous":
        return None
    item = table.get_item(Key={"PK": f"POLL#{poll_id}", "SK": f"VOTE#{alias}"}).get("Item")
    return item.get("option") if item else None


def put_vote(poll_id: str, alias: str, option: str, voted_at: int) -> None:
    table.put_item(
        Item={
            "PK": f"POLL#{poll_id}",
            "SK": f"VOTE#{alias}",
            "option": option,
            "votedAt": voted_at,
        }
    )


def delete_vote(poll_id: str, alias: str) -> None:
    table.delete_item(Key={"PK": f"POLL#{poll_id}", "SK": f"VOTE#{alias}"})


def delete_all_votes(poll_id: str) -> None:
    votes = get_votes(poll_id)
    with table.batch_writer() as batch:
        for v in votes:
            batch.delete_item(Key={"PK": f"POLL#{poll_id}", "SK": f"VOTE#{v.alias}"})
