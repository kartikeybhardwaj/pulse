"""Poll database operations."""

import json

from lib.db import table
from lib.models.poll import Poll


def get_poll(poll_id: str) -> Poll | None:
    item = table.get_item(Key={"PK": f"POLL#{poll_id}", "SK": "META"}).get("Item")
    return Poll.from_db(item) if item else None


def create_poll(item: dict) -> None:
    table.put_item(Item=item)


def update_poll_status(poll_id: str, status: str) -> None:
    table.update_item(
        Key={"PK": f"POLL#{poll_id}", "SK": "META"},
        UpdateExpression="SET #s = :s",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={":s": status},
    )


def update_poll_content(
    poll_id: str,
    question: str,
    description: str | None,
    options: list[str],
    question_link: str | None,
    option_links: list[str | None],
) -> None:
    table.update_item(
        Key={"PK": f"POLL#{poll_id}", "SK": "META"},
        UpdateExpression="SET question = :q, description = :d, options = :o, questionLink = :ql, optionLinks = :ol",
        ExpressionAttributeValues={
            ":q": question,
            ":d": description,
            ":o": options,
            ":ql": question_link,
            ":ol": option_links,
        },
    )


def delete_poll_and_votes(poll_id: str) -> None:
    from lib.db.votes import get_votes

    votes = get_votes(poll_id)
    with table.batch_writer() as batch:
        batch.delete_item(Key={"PK": f"POLL#{poll_id}", "SK": "META"})
        for v in votes:
            batch.delete_item(Key={"PK": f"POLL#{poll_id}", "SK": f"VOTE#{v.alias}"})


def query_polls(index: str, pk_value: str, page_size: int, cursor: str | None = None) -> tuple[list[Poll], dict | None]:
    pk_attr = f"{index}PK"
    params = {
        "IndexName": index,
        "KeyConditionExpression": "#pk = :pk",
        "ExpressionAttributeNames": {"#pk": pk_attr},
        "ExpressionAttributeValues": {":pk": pk_value},
        "ScanIndexForward": False,
        "Limit": page_size,
    }
    if cursor:
        params["ExclusiveStartKey"] = json.loads(cursor)
    r = table.query(**params)
    polls = [Poll.from_db(item) for item in r.get("Items", [])]
    return polls, r.get("LastEvaluatedKey")
