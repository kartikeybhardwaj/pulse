"""WebSocket $connect handler."""

from lib.db.connections import put_connection
from lib.utils import now_ts


def handler(event, context):
    put_connection(event["requestContext"]["connectionId"], now_ts())
    return {"statusCode": 200}
