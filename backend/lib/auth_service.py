"""Auth helpers — password hashing, JWT tokens, email sending.

JWT format: "username:expiry_timestamp:hmac_signature"
  - Signed with HMAC-SHA256 using a secret from SSM Parameter Store
  - Secret is loaded once per Lambda cold start and cached in memory
  - Token expiry: 30 days

Password hashing: PBKDF2-SHA256 with 100k iterations + random 16-byte salt
"""

import hashlib
import hmac
import os
import random
import secrets
import time

import boto3

# Cached across invocations within the same Lambda container
TOKEN_SECRET = None
TOKEN_EXPIRY = 86400 * 30  # 30 days
SES_FROM = os.environ.get("SES_FROM_EMAIL", "no-reply@example.com")

_ses = None
_ssm = None


def _get_ses():
    global _ses
    if _ses is None:
        _ses = boto3.client("ses", region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))
    return _ses


def _get_ssm():
    global _ssm
    if _ssm is None:
        _ssm = boto3.client("ssm", region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))
    return _ssm


def _get_secret() -> str:
    """Load JWT signing secret from SSM Parameter Store. Cached after first call."""
    global TOKEN_SECRET
    if not TOKEN_SECRET:
        param = os.environ.get("JWT_SECRET_PARAM", "/pulse/jwt-secret")
        TOKEN_SECRET = _get_ssm().get_parameter(Name=param)["Parameter"]["Value"]
    return TOKEN_SECRET


def hash_password(password: str, salt: str = None) -> tuple[str, str]:
    """Hash password with PBKDF2-SHA256. Returns (hash_hex, salt_hex).
    Pass existing salt to verify; omit to generate a new one."""
    if not salt:
        salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000).hex()
    return hashed, salt


def make_token(username: str) -> str:
    """Create a signed JWT-like token: "username:expiry:signature"."""
    secret = _get_secret()
    exp = int(time.time()) + TOKEN_EXPIRY
    payload = f"{username}:{exp}"
    sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}:{sig}"


def verify_token(token: str) -> str | None:
    """Verify token signature and expiry. Returns username or None."""
    try:
        secret = _get_secret()
        parts = token.split(":")
        if len(parts) != 3:
            return None
        username, exp, sig = parts
        expected = hmac.new(secret.encode(), f"{username}:{exp}".encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        if int(exp) < int(time.time()):
            return None
        return username
    except Exception:
        return None


def gen_code() -> str:
    """Generate a random 6-digit verification code."""
    return str(random.randint(100000, 999999))


def send_code(email: str, code: str, subject: str = "Pulse — Verify your email") -> None:
    """Send a verification/reset code via SES."""
    _get_ses().send_email(
        Source=os.environ.get("SES_FROM_EMAIL", "no-reply@example.com"),
        Destination={"ToAddresses": [email]},
        Message={
            "Subject": {"Data": subject},
            "Body": {"Text": {"Data": f"Your code is: {code}\n\nThis code expires in 10 minutes."}},
        },
    )
