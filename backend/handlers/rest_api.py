"""REST API handler — poll CRUD, voting, listing.

Routes:
  GET    /api/polls              — list recent or user's polls (paginated)
  POST   /api/polls              — create a new poll
  GET    /api/polls/{pollId}     — get poll with results
  DELETE /api/polls/{pollId}     — delete poll (creator only)
  PUT    /api/polls/{pollId}     — edit poll (creator only, resets votes if options change)
  PATCH  /api/polls/{pollId}     — toggle close/reopen (creator only)
  POST   /api/polls/{pollId}/vote — cast, switch, or undo a vote
"""

import json

from lib.db.polls import (
    get_poll,
    create_poll,
    update_poll_status,
    update_poll_content,
    delete_poll_and_votes,
    query_polls,
)
from lib.db.votes import get_votes, get_user_vote, put_vote, delete_vote, delete_all_votes
from lib.models.poll import Poll
from lib.response import response
from lib.utils import gen_id, now_ts, sanitize_url, EXPIRY_MAP, DATA_TTL, MAX_EXPIRY
from lib.polls import strip_poll_for_response
from lib.broadcast import broadcast_poll_update
from lib.auth_service import verify_token


def handler(event, context):
    method = event["httpMethod"]
    path = event.get("resource", "")
    headers = event.get("headers") or {}

    # Extract user from JWT token; unauthenticated users are "anonymous"
    alias = None
    auth = headers.get("Authorization") or headers.get("authorization") or ""
    if auth.startswith("Bearer "):
        alias = verify_token(auth[7:])
    if not alias:
        alias = "anonymous"

    path_params = event.get("pathParameters") or {}
    poll_id = path_params.get("pollId")

    # Route dispatch — matches API Gateway resource path + HTTP method
    try:
        routes = {
            ("/api/polls", "GET"): lambda: _list_polls(event, alias),
            ("/api/polls", "POST"): lambda: _create_poll(event, alias),
            ("/api/polls/{pollId}", "GET"): lambda: _get_poll(poll_id, alias),
            ("/api/polls/{pollId}", "DELETE"): lambda: _delete_poll(poll_id, alias),
            ("/api/polls/{pollId}", "PUT"): lambda: _edit_poll(poll_id, event, alias),
            ("/api/polls/{pollId}", "PATCH"): lambda: _close_poll(poll_id, alias),
            ("/api/polls/{pollId}/vote", "POST"): lambda: _vote(poll_id, event, alias),
        }
        fn = routes.get((path, method))
        return fn() if fn else response(404, {"error": "Not found"})
    except Exception as e:
        return response(500, {"error": str(e)})


def _create_poll(event, alias):
    body = json.loads(event.get("body") or "{}")
    question = body.get("question", "").strip()[:140]
    options = [o.strip()[:140] for o in body.get("options", [])]
    if not question or len(options) < 2 or len(options) > 5:
        return response(400, {"error": "Need question and 2-5 options"})

    poll_id = gen_id()
    ts = now_ts()

    # Custom schedule: startsAt/endsAt are unix timestamps from the frontend
    starts_at = int(body["startsAt"]) if body.get("startsAt") else None
    ends_at = int(body["endsAt"]) if body.get("endsAt") else None

    if starts_at and starts_at < ts:
        return response(400, {"error": "Start time cannot be in the past"})
    if ends_at and ends_at > ts + MAX_EXPIRY:
        return response(400, {"error": "End time cannot be more than 4 months from now"})
    if ends_at and starts_at and ends_at <= starts_at:
        return response(400, {"error": "End time must be after start time"})

    # endsAt (custom schedule) takes priority over expiry shortcut (dropdown)
    expiry = body.get("expiry")
    expires_at = ends_at if ends_at else ts + EXPIRY_MAP.get(expiry, 86400)
    deletes_at = ts + DATA_TTL  # all poll data auto-deleted after 6 months

    # DynamoDB single-table item with GSI keys for listing
    # GSI1: POLLS partition — recent polls (sorted by time)
    # GSI2: CREATOR#<alias> — user's own polls
    create_poll(
        {
            "PK": f"POLL#{poll_id}",
            "SK": "META",
            "GSI1PK": "POLLS",
            "GSI1SK": f"T#{ts}",
            "GSI2PK": f"CREATOR#{alias}",
            "GSI2SK": f"T#{ts}",
            "pollId": poll_id,
            "question": question,
            "description": (body.get("description") or "")[:160].strip() or None,
            "questionLink": sanitize_url(body.get("questionLink")),
            "options": options,
            "optionLinks": [sanitize_url(lnk) for lnk in body.get("optionLinks", [""] * len(options))],
            "creator": alias,
            # "scheduled" if start time is in the future; _check_expiry transitions it to "active"
            "status": "scheduled" if starts_at and starts_at > ts else "active",
            "createdAt": ts,
            "startsAt": starts_at,
            "expiresAt": expires_at,
            "deletesAt": deletes_at,
            "ttl": deletes_at,  # DynamoDB TTL — auto-deletes the item
            "anonCreator": bool(body.get("anonCreator")),
            "anonVoters": bool(body.get("anonVoters")),
            "visibleVoters": bool(body.get("visibleVoters")),
            "private": bool(body.get("private")),
        }
    )
    return response(201, {"pollId": poll_id})


def _get_poll(poll_id, alias):
    poll = get_poll(poll_id)
    if not poll:
        return response(404, {"error": "Poll not found"})
    _check_expiry(poll)
    return response(200, strip_poll_for_response(poll, get_votes(poll_id), alias))


def _list_polls(event, alias):
    qs = event.get("queryStringParameters") or {}
    filter_type = qs.get("filter", "recent")
    page_size = min(int(qs.get("limit", "10")), 50)
    cursor = qs.get("cursor")  # opaque DynamoDB LastEvaluatedKey from previous page

    # "mine" uses GSI2 (CREATOR#<alias>), "recent" uses GSI1 (POLLS)
    if filter_type == "mine":
        polls, last_key = query_polls("GSI2", f"CREATOR#{alias}", page_size, cursor)
    else:
        polls, last_key = query_polls("GSI1", "POLLS", page_size, cursor)
        # Private polls are excluded from the public recent feed
        polls = [p for p in polls if not p.private][:page_size]

    items = []
    for p in polls:
        _check_expiry(p)
        items.append(
            {
                "pollId": p.poll_id,
                "question": p.question,
                "options": p.options,
                "status": p.status,
                "createdAt": p.created_at,
                "startsAt": p.starts_at,
                "expiresAt": p.expires_at,
                "deletesAt": p.deletes_at,
                "anonCreator": p.anon_creator,
                "anonVoters": p.anon_voters,
                "private": p.private,
                "isOwner": p.creator == alias,
                "totalVotes": 0,
                "myVote": get_user_vote(p.poll_id, alias),
                "creator": "Anonymous" if p.anon_creator else p.creator,
            }
        )

    # Cursor for next page — None if no more results
    next_cursor = json.dumps(last_key, default=str) if last_key and len(polls) == page_size else None
    return response(200, {"polls": items, "nextCursor": next_cursor})


def _close_poll(poll_id, alias):
    """Toggle poll status: active → closed, closed → active. Expired polls cannot be reopened."""
    poll = get_poll(poll_id)
    if not poll:
        return response(404, {"error": "Poll not found"})
    if poll.creator != alias:
        return response(403, {"error": "Not the poll creator"})
    if poll.status == "expired":
        return response(400, {"error": "Expired polls cannot be reopened"})

    new_status = "active" if poll.status == "closed" else "closed"
    update_poll_status(poll_id, new_status)
    poll.status = new_status
    broadcast_poll_update(poll_id, {"type": "update", "poll": strip_poll_for_response(poll, get_votes(poll_id), "")})
    return response(200, {"status": new_status})


def _edit_poll(poll_id, event, alias):
    poll = get_poll(poll_id)
    if not poll:
        return response(404, {"error": "Poll not found"})
    if poll.creator != alias:
        return response(403, {"error": "Not the poll creator"})
    if poll.status != "active":
        return response(400, {"error": "Can only edit active polls"})

    body = json.loads(event.get("body") or "{}")
    question = body.get("question", "").strip()[:140]
    options = [o.strip()[:140] for o in body.get("options", [])]
    if not question or len(options) < 2 or len(options) > 5:
        return response(400, {"error": "Need question and 2-5 options"})

    # If options changed (added/removed/renamed), all existing votes become
    # invalid — delete them and notify viewers via "reset" broadcast
    options_changed = options != poll.options
    if options_changed:
        delete_all_votes(poll_id)

    update_poll_content(
        poll_id,
        question,
        (body.get("description") or "")[:160].strip() or None,
        options,
        sanitize_url(body.get("questionLink")),
        [sanitize_url(lnk) for lnk in body.get("optionLinks", [""] * len(options))],
    )

    poll.question = question
    poll.options = options
    votes = [] if options_changed else get_votes(poll_id)
    broadcast_poll_update(
        poll_id,
        {
            "type": "reset" if options_changed else "update",
            "poll": strip_poll_for_response(poll, votes, ""),
        },
    )
    return response(200, {"edited": True, "votesReset": options_changed})


def _delete_poll(poll_id, alias):
    poll = get_poll(poll_id)
    if not poll:
        return response(404, {"error": "Poll not found"})
    if poll.creator != alias:
        return response(403, {"error": "Not the poll creator"})

    delete_poll_and_votes(poll_id)
    broadcast_poll_update(poll_id, {"type": "deleted", "pollId": poll_id})
    return response(200, {"deleted": True})


def _vote(poll_id, event, alias):
    """Cast, switch, or undo a vote.

    - Voting for a new option: creates/overwrites the vote
    - Voting for the same option you already voted for: removes the vote (undo)
    - One vote per user per poll, enforced by PK=POLL#id SK=VOTE#alias
    """
    poll = get_poll(poll_id)
    if not poll:
        return response(404, {"error": "Poll not found"})
    _check_expiry(poll)
    if poll.status != "active":
        return response(400, {"error": "Poll is not active"})

    body = json.loads(event.get("body") or "{}")
    option = body.get("option", "")
    if option not in poll.options:
        return response(400, {"error": "Invalid option"})

    # Same option = undo vote
    current = get_user_vote(poll_id, alias)
    if current == option:
        delete_vote(poll_id, alias)
        broadcast_poll_update(
            poll_id, {"type": "update", "poll": strip_poll_for_response(poll, get_votes(poll_id), "")}
        )
        return response(200, {"voted": None})

    put_vote(poll_id, alias, option, now_ts())
    broadcast_poll_update(poll_id, {"type": "update", "poll": strip_poll_for_response(poll, get_votes(poll_id), "")})
    return response(200, {"voted": option})


def _check_expiry(poll: Poll):
    """Lazily transition poll status based on current time.

    Called on every read — handles two transitions:
      scheduled → active  (when startsAt has passed)
      active → expired    (when expiresAt has passed)
    Writes the new status to DynamoDB so subsequent reads are consistent.
    """
    ts = now_ts()
    new_status = None

    if poll.status == "scheduled" and poll.starts_at and ts >= poll.starts_at:
        new_status = "active"
    if (poll.status == "active" or new_status == "active") and poll.expires_at and ts > poll.expires_at:
        new_status = "expired"

    if new_status and new_status != poll.status:
        poll.status = new_status
        update_poll_status(poll.poll_id, new_status)
