"""Tests for model dataclasses — from_db conversion."""

from lib.models.user import User
from lib.models.poll import Poll
from lib.models.vote import Vote


class TestUserModel:
    def test_from_db(self):
        item = {
            "username": "alice",
            "email": "alice@test.com",
            "passwordHash": "abc123",
            "salt": "def456",
            "verified": True,
            "createdAt": 1000,
        }
        user = User.from_db(item)
        assert user.username == "alice"
        assert user.email == "alice@test.com"
        assert user.verified is True
        assert user.verify_code is None

    def test_from_db_with_codes(self):
        item = {
            "username": "bob",
            "email": "bob@test.com",
            "passwordHash": "h",
            "salt": "s",
            "verified": False,
            "verifyCode": "123456",
            "verifyCodeExp": 9999999999,
            "resetCode": "654321",
            "resetCodeExp": 9999999999,
        }
        user = User.from_db(item)
        assert user.verify_code == "123456"
        assert user.reset_code == "654321"


class TestPollModel:
    def test_from_db(self):
        item = {
            "pollId": "abc123",
            "question": "Favorite color?",
            "options": ["Red", "Blue"],
            "creator": "alice",
            "status": "active",
            "createdAt": 1000,
            "anonCreator": True,
            "anonVoters": False,
            "visibleVoters": True,
            "private": False,
        }
        poll = Poll.from_db(item)
        assert poll.poll_id == "abc123"
        assert poll.question == "Favorite color?"
        assert poll.options == ["Red", "Blue"]
        assert poll.anon_creator is True
        assert poll.starts_at is None

    def test_from_db_with_schedule(self):
        item = {
            "pollId": "x",
            "question": "Q",
            "options": ["A"],
            "creator": "bob",
            "status": "scheduled",
            "startsAt": 2000,
            "expiresAt": 3000,
            "deletesAt": 4000,
        }
        poll = Poll.from_db(item)
        assert poll.status == "scheduled"
        assert poll.starts_at == 2000
        assert poll.expires_at == 3000


class TestVoteModel:
    def test_from_db(self):
        item = {
            "PK": "POLL#abc123",
            "SK": "VOTE#alice",
            "option": "Red",
            "votedAt": 1000,
        }
        vote = Vote.from_db(item)
        assert vote.poll_id == "abc123"
        assert vote.alias == "alice"
        assert vote.option == "Red"
