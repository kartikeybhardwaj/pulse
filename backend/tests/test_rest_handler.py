"""Integration tests for the REST API handler — poll CRUD, voting."""

import json
from handlers.rest_api import handler


def _call(path: str, method: str = "GET", body: dict = None, alias: str = "testuser", poll_id: str = None) -> dict:
    """Helper to invoke the REST handler with a test JWT."""
    from lib.auth_service import make_token

    event = {
        "httpMethod": method,
        "resource": path,
        "body": json.dumps(body) if body else "{}",
        "headers": {"Authorization": f"Bearer {make_token(alias)}"},
        "pathParameters": {"pollId": poll_id} if poll_id else None,
        "queryStringParameters": {},
    }
    resp = handler(event, None)
    resp["_body"] = json.loads(resp["body"]) if resp["body"] else {}
    return resp


def _create_poll(question="Test?", options=None) -> str:
    """Create a poll and return its ID."""
    r = _call(
        "/api/polls",
        "POST",
        body={
            "question": question,
            "options": options or ["A", "B"],
            "expiry": "24h",
        },
    )
    assert r["statusCode"] == 201
    return r["_body"]["pollId"]


class TestCreatePoll:
    def test_create_success(self):
        r = _call("/api/polls", "POST", body={"question": "Fav?", "options": ["X", "Y"], "expiry": "1h"})
        assert r["statusCode"] == 201
        assert "pollId" in r["_body"]

    def test_create_too_few_options(self):
        r = _call("/api/polls", "POST", body={"question": "Q?", "options": ["Only one"]})
        assert r["statusCode"] == 400

    def test_create_too_many_options(self):
        r = _call("/api/polls", "POST", body={"question": "Q?", "options": ["A", "B", "C", "D", "E", "F"]})
        assert r["statusCode"] == 400

    def test_create_empty_question(self):
        r = _call("/api/polls", "POST", body={"question": "", "options": ["A", "B"]})
        assert r["statusCode"] == 400

    def test_create_with_description(self):
        r = _call(
            "/api/polls",
            "POST",
            body={
                "question": "Q?",
                "options": ["A", "B"],
                "description": "Some context",
                "expiry": "24h",
            },
        )
        assert r["statusCode"] == 201


class TestGetPoll:
    def test_get_existing(self):
        poll_id = _create_poll()
        r = _call("/api/polls/{pollId}", "GET", poll_id=poll_id)
        assert r["statusCode"] == 200
        assert r["_body"]["question"] == "Test?"

    def test_get_nonexistent(self):
        r = _call("/api/polls/{pollId}", "GET", poll_id="doesnotexist")
        assert r["statusCode"] == 404


class TestListPolls:
    def test_list_recent(self):
        _create_poll("Poll 1")
        _create_poll("Poll 2")
        r = _call("/api/polls", "GET")
        assert r["statusCode"] == 200
        assert len(r["_body"]["polls"]) >= 2

    def test_private_excluded_from_recent(self):
        r = _call(
            "/api/polls",
            "POST",
            body={
                "question": "Secret?",
                "options": ["A", "B"],
                "private": True,
                "expiry": "24h",
            },
        )
        poll_id = r["_body"]["pollId"]

        r = _call("/api/polls", "GET")
        poll_ids = [p["pollId"] for p in r["_body"]["polls"]]
        assert poll_id not in poll_ids


class TestVoting:
    def test_vote_success(self):
        poll_id = _create_poll()
        r = _call("/api/polls/{pollId}/vote", "POST", body={"option": "A"}, poll_id=poll_id)
        assert r["statusCode"] == 200

    def test_vote_invalid_option(self):
        poll_id = _create_poll()
        r = _call("/api/polls/{pollId}/vote", "POST", body={"option": "Z"}, poll_id=poll_id)
        assert r["statusCode"] == 400

    def test_vote_undo(self):
        """Voting for the same option twice should undo the vote."""
        poll_id = _create_poll()
        # Vote
        _call("/api/polls/{pollId}/vote", "POST", body={"option": "A"}, poll_id=poll_id)
        # Undo
        r = _call("/api/polls/{pollId}/vote", "POST", body={"option": "A"}, poll_id=poll_id)
        assert r["_body"]["voted"] is None


class TestClosePoll:
    def test_close_and_reopen(self):
        poll_id = _create_poll()
        # Close
        r = _call("/api/polls/{pollId}", "PATCH", poll_id=poll_id)
        assert r["_body"]["status"] == "closed"
        # Reopen
        r = _call("/api/polls/{pollId}", "PATCH", poll_id=poll_id)
        assert r["_body"]["status"] == "active"


class TestDeletePoll:
    def test_delete(self):
        poll_id = _create_poll()
        r = _call("/api/polls/{pollId}", "DELETE", poll_id=poll_id)
        assert r["statusCode"] == 200
        assert r["_body"]["deleted"] is True

        # Should be gone
        r = _call("/api/polls/{pollId}", "GET", poll_id=poll_id)
        assert r["statusCode"] == 404


class TestEditPoll:
    def test_edit_question(self):
        poll_id = _create_poll()
        r = _call(
            "/api/polls/{pollId}",
            "PUT",
            body={
                "question": "Updated?",
                "options": ["A", "B"],
            },
            poll_id=poll_id,
        )
        assert r["statusCode"] == 200
        assert r["_body"]["votesReset"] is False

    def test_edit_options_resets_votes(self):
        poll_id = _create_poll()
        # Vote first
        _call("/api/polls/{pollId}/vote", "POST", body={"option": "A"}, poll_id=poll_id)
        # Edit options
        r = _call(
            "/api/polls/{pollId}",
            "PUT",
            body={
                "question": "Test?",
                "options": ["X", "Y"],
            },
            poll_id=poll_id,
        )
        assert r["_body"]["votesReset"] is True
