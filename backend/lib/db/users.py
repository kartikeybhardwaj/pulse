"""User database operations."""

from lib.db import table
from lib.models.user import User


def get_user(username: str) -> User | None:
    item = table.get_item(Key={"PK": f"USER#{username}", "SK": "PROFILE"}).get("Item")
    return User.from_db(item) if item else None


def get_user_by_email(email: str) -> tuple[str | None, User | None]:
    lookup = table.get_item(Key={"PK": f"EMAIL#{email}", "SK": "LOOKUP"}).get("Item")
    if not lookup:
        return None, None
    return lookup["username"], get_user(lookup["username"])


def create_user(user: User) -> None:
    table.put_item(
        Item={
            "PK": f"USER#{user.username}",
            "SK": "PROFILE",
            "username": user.username,
            "email": user.email,
            "passwordHash": user.password_hash,
            "salt": user.salt,
            "verified": user.verified,
            "verifyCode": user.verify_code,
            "verifyCodeExp": user.verify_code_exp,
            "createdAt": user.created_at,
        }
    )
    table.put_item(Item={"PK": f"EMAIL#{user.email}", "SK": "LOOKUP", "username": user.username})


def verify_user(username: str) -> None:
    table.update_item(
        Key={"PK": f"USER#{username}", "SK": "PROFILE"},
        UpdateExpression="SET verified = :v REMOVE verifyCode, verifyCodeExp",
        ExpressionAttributeValues={":v": True},
    )


def update_verify_code(username: str, code: str, exp: int) -> None:
    table.update_item(
        Key={"PK": f"USER#{username}", "SK": "PROFILE"},
        UpdateExpression="SET verifyCode = :c, verifyCodeExp = :e",
        ExpressionAttributeValues={":c": code, ":e": exp},
    )


def update_reset_code(username: str, code: str, exp: int) -> None:
    table.update_item(
        Key={"PK": f"USER#{username}", "SK": "PROFILE"},
        UpdateExpression="SET resetCode = :c, resetCodeExp = :e",
        ExpressionAttributeValues={":c": code, ":e": exp},
    )


def update_password(username: str, password_hash: str, salt: str) -> None:
    table.update_item(
        Key={"PK": f"USER#{username}", "SK": "PROFILE"},
        UpdateExpression="SET passwordHash = :h, salt = :s REMOVE resetCode, resetCodeExp",
        ExpressionAttributeValues={":h": password_hash, ":s": salt},
    )
