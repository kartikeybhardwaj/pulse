"""Tests for the response builder and Decimal encoding."""

import json
from decimal import Decimal
from lib.response import response


class TestResponse:
    def test_status_and_headers(self):
        r = response(200, {"ok": True})
        assert r["statusCode"] == 200
        assert r["headers"]["Content-Type"] == "application/json"
        assert r["headers"]["Access-Control-Allow-Origin"] == "*"

    def test_body_serialized(self):
        r = response(200, {"key": "value"})
        assert json.loads(r["body"]) == {"key": "value"}

    def test_empty_body(self):
        r = response(204)
        assert r["body"] == ""

    def test_decimal_int(self):
        """DynamoDB returns integers as Decimal — should serialize as int."""
        r = response(200, {"count": Decimal("42")})
        body = json.loads(r["body"])
        assert body["count"] == 42
        assert isinstance(body["count"], int)

    def test_decimal_float(self):
        """DynamoDB returns floats as Decimal — should serialize as float."""
        r = response(200, {"score": Decimal("3.14")})
        body = json.loads(r["body"])
        assert body["score"] == 3.14

    def test_global_encoder_works(self):
        """json.dumps should handle Decimals globally after response module is imported."""
        result = json.dumps({"val": Decimal("99")})
        assert '"val": 99' in result
