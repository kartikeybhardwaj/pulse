"""Auth handler — signup, verify, signin, password reset.

Routes:
  POST /api/auth/signup  — register with username, email, password → sends 6-digit code via SES
  POST /api/auth/verify  — submit code to verify email → returns JWT
  POST /api/auth/resend  — resend verification code
  POST /api/auth/signin  — login with email + password → returns JWT (must be verified)
  POST /api/auth/forgot  — request password reset code via email
  POST /api/auth/reset   — submit reset code + new password → returns JWT
  GET  /api/auth/me      — validate JWT, return username

Auth flow:
  signup → verify email → signin
  forgot → reset → auto-signin
"""

import json
import time

from lib.db.users import (
    get_user,
    get_user_by_email,
    create_user,
    verify_user,
    update_verify_code,
    update_reset_code,
    update_password,
)
from lib.models.user import User
from lib.response import response
from lib.auth_service import hash_password, make_token, verify_token, gen_code, send_code


def handler(event, context):
    method = event["httpMethod"]
    path = event.get("resource", "")
    body = json.loads(event.get("body") or "{}")

    try:
        routes = {
            ("/api/auth/signup", "POST"): lambda: _signup(body),
            ("/api/auth/verify", "POST"): lambda: _verify(body),
            ("/api/auth/resend", "POST"): lambda: _resend(body),
            ("/api/auth/signin", "POST"): lambda: _signin(body),
            ("/api/auth/forgot", "POST"): lambda: _forgot(body),
            ("/api/auth/reset", "POST"): lambda: _reset(body),
            ("/api/auth/me", "GET"): lambda: _me(event),
        }
        fn = routes.get((path, method))
        return fn() if fn else response(404, {"error": "Not found"})
    except Exception as e:
        return response(500, {"error": str(e)})


def _signup(body):
    username = (body.get("username") or "").strip().lower()
    email = (body.get("email") or "").strip().lower()
    password = body.get("password") or ""

    if not username or not email or len(password) < 6:
        return response(400, {"error": "Username, email, and password (6+ chars) required"})
    if len(username) < 3 or len(username) > 30:
        return response(400, {"error": "Username must be 3-30 characters"})
    if get_user(username):
        return response(409, {"error": "Username already taken"})

    existing_username, _ = get_user_by_email(email)
    if existing_username:
        return response(409, {"error": "Email already registered"})

    hashed, salt = hash_password(password)
    code = gen_code()
    ts = int(time.time())

    # User is created as unverified — must complete email verification before signin
    create_user(
        User(
            username=username,
            email=email,
            password_hash=hashed,
            salt=salt,
            verified=False,
            verify_code=code,
            verify_code_exp=ts + 600,
            created_at=ts,
        )
    )
    send_code(email, code, "Pulse — Verify your email")
    return response(201, {"message": "Verification code sent", "email": email})


def _verify(body):
    """Verify email with 6-digit code. Returns JWT on success."""
    email = (body.get("email") or "").strip().lower()
    code = (body.get("code") or "").strip()
    if not email or not code:
        return response(400, {"error": "Email and code required"})

    username, user = get_user_by_email(email)
    if not user:
        return response(404, {"error": "Email not found"})
    if user.verified:
        return response(200, {"message": "Already verified"})
    if user.verify_code != code:
        return response(400, {"error": "Invalid code"})
    if int(time.time()) > (user.verify_code_exp or 0):
        return response(400, {"error": "Code expired — request a new one"})

    verify_user(username)
    return response(200, {"token": make_token(username), "username": username})


def _resend(body):
    email = (body.get("email") or "").strip().lower()
    if not email:
        return response(400, {"error": "Email required"})

    username, user = get_user_by_email(email)
    if not user or user.verified:
        return response(400, {"error": "Already verified"})

    code = gen_code()
    update_verify_code(username, code, int(time.time()) + 600)
    send_code(email, code, "Pulse — Verify your email")
    return response(200, {"message": "New code sent"})


def _forgot(body):
    """Send password reset code. Doesn't reveal whether email exists."""
    email = (body.get("email") or "").strip().lower()
    if not email:
        return response(400, {"error": "Email required"})

    username, user = get_user_by_email(email)
    if not user:
        # Same response whether email exists or not — prevents email enumeration
        return response(200, {"message": "If that email is registered, a reset code has been sent"})

    code = gen_code()
    update_reset_code(username, code, int(time.time()) + 600)
    send_code(email, code, "Pulse — Password reset code")
    return response(200, {"message": "If that email is registered, a reset code has been sent"})


def _reset(body):
    """Reset password with 6-digit code. Returns JWT on success (auto-signin)."""
    email = (body.get("email") or "").strip().lower()
    code = (body.get("code") or "").strip()
    new_password = body.get("password") or ""
    if not email or not code or len(new_password) < 6:
        return response(400, {"error": "Email, code, and new password (6+ chars) required"})

    username, user = get_user_by_email(email)
    if not user or user.reset_code != code:
        return response(400, {"error": "Invalid code"})
    if int(time.time()) > (user.reset_code_exp or 0):
        return response(400, {"error": "Code expired — request a new one"})

    hashed, salt = hash_password(new_password)
    update_password(username, hashed, salt)
    return response(200, {"token": make_token(username), "username": username})


def _signin(body):
    email = (body.get("email") or "").strip().lower()
    password = body.get("password") or ""
    if not email or not password:
        return response(400, {"error": "Email and password required"})

    username, user = get_user_by_email(email)
    if not user:
        return response(401, {"error": "Invalid email or password"})
    # Unverified users get a 403 with a flag so the frontend can redirect to verification
    if not user.verified:
        return response(403, {"error": "Email not verified", "needsVerification": True, "email": email})

    hashed, _ = hash_password(password, user.salt)
    if hashed != user.password_hash:
        return response(401, {"error": "Invalid email or password"})

    return response(200, {"token": make_token(username), "username": username})


def _me(event):
    """Validate JWT and return the username. Used by frontend to check session."""
    headers = event.get("headers") or {}
    auth = headers.get("Authorization") or headers.get("authorization") or ""
    token = auth.replace("Bearer ", "") if auth.startswith("Bearer ") else ""
    username = verify_token(token)
    if not username:
        return response(401, {"error": "Not authenticated"})
    return response(200, {"username": username})
