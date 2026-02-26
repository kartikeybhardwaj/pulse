"""Tests for poll response builder — anonymity enforcement."""

from lib.models.poll import Poll
from lib.models.vote import Vote
from lib.polls import strip_poll_for_response


def _make_poll(**overrides) -> Poll:
    defaults = dict(
        poll_id="p1",
        question="Q?",
        options=["A", "B"],
        creator="alice",
        status="active",
        created_at=1000,
        expires_at=9999999999,
        deletes_at=9999999999,
    )
    return Poll(**{**defaults, **overrides})


def _make_vote(alias: str, option: str) -> Vote:
    return Vote(poll_id="p1", alias=alias, option=option, voted_at=1000)


class TestStripPollForResponse:
    def test_basic_response(self):
        poll = _make_poll()
        votes = [_make_vote("alice", "A"), _make_vote("bob", "B")]
        result = strip_poll_for_response(poll, votes, "alice")

        assert result["pollId"] == "p1"
        assert result["totalVotes"] == 2
        assert result["myVote"] == "A"
        assert result["isOwner"] is True

    def test_anon_creator_hides_name(self):
        poll = _make_poll(anon_creator=True)
        result = strip_poll_for_response(poll, [], "bob")

        assert result["creator"] == "Anonymous"
        assert result["isOwner"] is False  # bob is not the creator

    def test_anon_voters_hides_voter_list(self):
        """When anon_voters is True, no voter names should appear even if visible_voters is True."""
        poll = _make_poll(anon_voters=True, visible_voters=True)
        votes = [_make_vote("alice", "A"), _make_vote("bob", "A")]
        result = strip_poll_for_response(poll, votes, "alice")

        # Counts should still work
        assert result["results"][0]["count"] == 2
        # But no voter list
        assert "voters" not in result["results"][0]

    def test_visible_voters_shows_names(self):
        poll = _make_poll(visible_voters=True)
        votes = [_make_vote("alice", "A"), _make_vote("bob", "B")]
        result = strip_poll_for_response(poll, votes, "alice")

        assert result["results"][0]["voters"] == ["alice"]
        assert result["results"][1]["voters"] == ["bob"]

    def test_anonymous_user_gets_no_my_vote(self):
        """The "anonymous" user should never see a myVote — prevents shared identity leaking."""
        poll = _make_poll()
        votes = [_make_vote("anonymous", "A")]
        result = strip_poll_for_response(poll, votes, "anonymous")

        assert result["myVote"] is None

    def test_option_links_included(self):
        poll = _make_poll(option_links=["https://a.com", None])
        result = strip_poll_for_response(poll, [], "alice")

        assert result["results"][0]["link"] == "https://a.com"
        assert "link" not in result["results"][1]

    def test_vote_counts_per_option(self):
        poll = _make_poll(options=["A", "B", "C"])
        votes = [_make_vote("a", "A"), _make_vote("b", "A"), _make_vote("c", "B")]
        result = strip_poll_for_response(poll, votes, "x")

        counts = {r["option"]: r["count"] for r in result["results"]}
        assert counts == {"A": 2, "B": 1, "C": 0}
