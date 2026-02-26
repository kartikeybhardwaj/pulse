"""Poll response builder with server-side anonymity enforcement.

This is the ONLY place where poll data is shaped for API responses.
Anonymity rules are enforced here — the API never returns data the frontend shouldn't show.
"""

from lib.models.poll import Poll
from lib.models.vote import Vote


def strip_poll_for_response(poll: Poll, votes: list[Vote], requester: str) -> dict:
    """Build a safe poll response, stripping data based on anonymity flags."""
    counts = {opt: 0 for opt in poll.options}
    voter_map = {opt: [] for opt in poll.options}
    requester_vote = None

    for v in votes:
        counts[v.option] = counts.get(v.option, 0) + 1
        if not poll.anon_voters and poll.visible_voters:
            voter_map[v.option].append(v.alias)
        if v.alias == requester and requester != "anonymous":
            requester_vote = v.option

    results = []
    option_links = poll.option_links or [None] * len(poll.options)
    for i, opt in enumerate(poll.options):
        entry = {"option": opt, "count": counts.get(opt, 0)}
        if i < len(option_links) and option_links[i]:
            entry["link"] = option_links[i]
        if not poll.anon_voters and poll.visible_voters:
            entry["voters"] = voter_map.get(opt, [])
        results.append(entry)

    return {
        "pollId": poll.poll_id,
        "question": poll.question,
        "description": poll.description,
        "questionLink": poll.question_link,
        "options": poll.options,
        "results": results,
        "totalVotes": sum(counts.values()),
        "status": poll.status,
        "createdAt": poll.created_at,
        "startsAt": poll.starts_at,
        "expiresAt": poll.expires_at,
        "deletesAt": poll.deletes_at,
        "anonCreator": poll.anon_creator,
        "anonVoters": poll.anon_voters,
        "visibleVoters": poll.visible_voters,
        "private": poll.private,
        "myVote": requester_vote,
        "creator": "Anonymous" if poll.anon_creator else poll.creator,
        "isOwner": poll.creator == requester,
    }
