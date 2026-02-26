"""Shared constants and utility functions.

Expiry options map frontend dropdown values to seconds.
MAX_EXPIRY and DATA_TTL control the upper bounds for poll lifetime.
"""

import random
import string
import time

# Frontend expiry dropdown → seconds
EXPIRY_MAP = {"1h": 3600, "6h": 21600, "24h": 86400, "7d": 604800, "30d": 2592000, "4mo": 10368000}
MAX_EXPIRY = 10368000  # 4 months — maximum voting window
DATA_TTL = 15552000  # 6 months — DynamoDB TTL auto-deletes poll data after this


def gen_id(length: int = 8) -> str:
    """Generate a short random alphanumeric ID for poll URLs (e.g., 'abc12def')."""
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))


def now_ts() -> int:
    """Current time as unix timestamp (seconds)."""
    return int(time.time())


def sanitize_url(url: str | None) -> str | None:
    """Only allow http/https URLs. Blocks javascript: and other XSS vectors."""
    if not url:
        return None
    url = url.strip()
    return url if url.startswith(("https://", "http://")) else None
