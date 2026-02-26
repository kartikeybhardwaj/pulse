"""Tests for auth_service — password hashing and JWT tokens."""

from lib.auth_service import hash_password, make_token, verify_token, gen_code


class TestPasswordHashing:
    def test_hash_and_verify(self):
        hashed, salt = hash_password("mypassword")
        assert hashed != "mypassword"  # not stored in plaintext
        assert len(salt) == 32  # 16 bytes hex

        # Same password + salt = same hash
        hashed2, _ = hash_password("mypassword", salt)
        assert hashed == hashed2

    def test_wrong_password(self):
        hashed, salt = hash_password("correct")
        wrong_hash, _ = hash_password("wrong", salt)
        assert hashed != wrong_hash

    def test_different_salts(self):
        h1, s1 = hash_password("same")
        h2, s2 = hash_password("same")
        assert s1 != s2  # random salt each time
        assert h1 != h2  # different salt = different hash


class TestJwtTokens:
    def test_make_and_verify(self):
        token = make_token("testuser")
        assert verify_token(token) == "testuser"

    def test_invalid_token(self):
        assert verify_token("garbage") is None
        assert verify_token("a:b:c") is None
        assert verify_token("") is None

    def test_tampered_signature(self):
        token = make_token("testuser")
        parts = token.split(":")
        parts[2] = "tampered"
        assert verify_token(":".join(parts)) is None

    def test_expired_token(self):
        """Token with expiry in the past should fail."""
        import hmac
        import hashlib

        secret = "test-secret-key-for-jwt"
        payload = "testuser:0"  # expired at epoch 0
        sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        assert verify_token(f"{payload}:{sig}") is None


class TestGenCode:
    def test_six_digits(self):
        code = gen_code()
        assert len(code) == 6
        assert code.isdigit()

    def test_randomness(self):
        codes = {gen_code() for _ in range(100)}
        assert len(codes) > 50  # should be mostly unique
