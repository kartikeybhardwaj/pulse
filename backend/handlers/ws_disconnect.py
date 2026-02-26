"""WebSocket $disconnect handler."""

from lib.db.connections import delete_connection


def handler(event, context):
    delete_connection(event["requestContext"]["connectionId"])
    return {"statusCode": 200}
