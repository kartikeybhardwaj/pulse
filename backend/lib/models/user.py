"""User model.

Maps to DynamoDB items with PK=USER#<username> SK=PROFILE.
Email lookup is a separate item: PK=EMAIL#<email> SK=LOOKUP.
"""

from dataclasses import dataclass


@dataclass
class User:
    username: str
    email: str
    password_hash: str
    salt: str
    verified: bool = False
    verify_code: str | None = None
    verify_code_exp: int | None = None
    reset_code: str | None = None
    reset_code_exp: int | None = None
    created_at: int = 0

    @classmethod
    def from_db(cls, item: dict) -> "User":
        return cls(
            username=item["username"],
            email=item["email"],
            password_hash=item["passwordHash"],
            salt=item["salt"],
            verified=item.get("verified", False),
            verify_code=item.get("verifyCode"),
            verify_code_exp=int(item["verifyCodeExp"]) if item.get("verifyCodeExp") else None,
            reset_code=item.get("resetCode"),
            reset_code_exp=int(item["resetCodeExp"]) if item.get("resetCodeExp") else None,
            created_at=int(item.get("createdAt", 0)),
        )
