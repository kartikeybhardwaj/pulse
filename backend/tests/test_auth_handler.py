"""Integration tests for the auth handler — signup, verify, signin, reset flows."""

import json
from handlers.auth import handler


def _call(path: str, method: str = "POST", body: dict = None, headers: dict = None) -> dict:
    event = {
        "httpMethod": method,
        "resource": path,
        "body": json.dumps(body) if body else "{}",
        "headers": headers or {},
    }
    resp = handler(event, None)
    resp["_body"] = json.loads(resp["body"]) if resp["body"] else {}
    return resp


class TestSignupFlow:
    def test_signup_success(self):
        r = _call("/api/auth/signup", body={"username": "alice", "email": "alice@test.com", "password": "pass123"})
        assert r["statusCode"] == 201, r["_body"]
        assert r["_body"]["email"] == "alice@test.com"

    def test_signup_duplicate_username(self):
        _call("/api/auth/signup", body={"username": "bob", "email": "bob1@test.com", "password": "pass123"})
        r = _call("/api/auth/signup", body={"username": "bob", "email": "bob2@test.com", "password": "pass123"})
        assert r["statusCode"] == 409
        assert "already taken" in r["_body"]["error"]

    def test_signup_duplicate_email(self):
        _call("/api/auth/signup", body={"username": "carol1", "email": "carol@test.com", "password": "pass123"})
        r = _call("/api/auth/signup", body={"username": "carol2", "email": "carol@test.com", "password": "pass123"})
        assert r["statusCode"] == 409
        assert "already registered" in r["_body"]["error"]

    def test_signup_short_password(self):
        r = _call("/api/auth/signup", body={"username": "dave", "email": "dave@test.com", "password": "12345"})
        assert r["statusCode"] == 400

    def test_signup_short_username(self):
        r = _call("/api/auth/signup", body={"username": "ab", "email": "ab@test.com", "password": "pass123"})
        assert r["statusCode"] == 400


class TestVerifyFlow:
    def test_verify_success(self):
        # Signup
        _call("/api/auth/signup", body={"username": "eve", "email": "eve@test.com", "password": "pass123"})

        # Get the code from DynamoDB directly
        from lib.db.users import get_user

        user = get_user("eve")
        code = user.verify_code

        # Verify
        r = _call("/api/auth/verify", body={"email": "eve@test.com", "code": code})
        assert r["statusCode"] == 200
        assert "token" in r["_body"]

    def test_verify_wrong_code(self):
        _call("/api/auth/signup", body={"username": "frank", "email": "frank@test.com", "password": "pass123"})
        r = _call("/api/auth/verify", body={"email": "frank@test.com", "code": "000000"})
        assert r["statusCode"] == 400
        assert "Invalid code" in r["_body"]["error"]


class TestSigninFlow:
    def _create_verified_user(self, username, email, password):
        _call("/api/auth/signup", body={"username": username, "email": email, "password": password})
        from lib.db.users import get_user

        code = get_user(username).verify_code
        _call("/api/auth/verify", body={"email": email, "code": code})

    def test_signin_success(self):
        self._create_verified_user("grace", "grace@test.com", "pass123")
        r = _call("/api/auth/signin", body={"email": "grace@test.com", "password": "pass123"})
        assert r["statusCode"] == 200
        assert "token" in r["_body"]

    def test_signin_wrong_password(self):
        self._create_verified_user("heidi", "heidi@test.com", "pass123")
        r = _call("/api/auth/signin", body={"email": "heidi@test.com", "password": "wrong"})
        assert r["statusCode"] == 401

    def test_signin_unverified(self):
        _call("/api/auth/signup", body={"username": "ivan", "email": "ivan@test.com", "password": "pass123"})
        r = _call("/api/auth/signin", body={"email": "ivan@test.com", "password": "pass123"})
        assert r["statusCode"] == 403
        assert r["_body"]["needsVerification"] is True

    def test_signin_nonexistent(self):
        r = _call("/api/auth/signin", body={"email": "nobody@test.com", "password": "pass123"})
        assert r["statusCode"] == 401


class TestMeEndpoint:
    def test_me_with_valid_token(self):
        _call("/api/auth/signup", body={"username": "judy", "email": "judy@test.com", "password": "pass123"})
        from lib.db.users import get_user

        code = get_user("judy").verify_code
        r = _call("/api/auth/verify", body={"email": "judy@test.com", "code": code})
        token = r["_body"]["token"]

        r = _call("/api/auth/me", method="GET", headers={"Authorization": f"Bearer {token}"})
        assert r["statusCode"] == 200
        assert r["_body"]["username"] == "judy"

    def test_me_without_token(self):
        r = _call("/api/auth/me", method="GET")
        assert r["statusCode"] == 401
