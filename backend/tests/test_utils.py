"""Tests for utility functions."""

from lib.utils import gen_id, now_ts, sanitize_url, EXPIRY_MAP, MAX_EXPIRY, DATA_TTL


class TestGenId:
    def test_default_length(self):
        assert len(gen_id()) == 8

    def test_custom_length(self):
        assert len(gen_id(12)) == 12

    def test_alphanumeric(self):
        for _ in range(50):
            assert gen_id().isalnum()

    def test_uniqueness(self):
        ids = {gen_id() for _ in range(100)}
        assert len(ids) > 90


class TestNowTs:
    def test_returns_int(self):
        assert isinstance(now_ts(), int)

    def test_reasonable_value(self):
        assert now_ts() > 1700000000  # after 2023


class TestSanitizeUrl:
    def test_valid_https(self):
        assert sanitize_url("https://example.com") == "https://example.com"

    def test_valid_http(self):
        assert sanitize_url("http://example.com") == "http://example.com"

    def test_javascript_blocked(self):
        assert sanitize_url("javascript:alert(1)") is None

    def test_data_uri_blocked(self):
        assert sanitize_url("data:text/html,<h1>xss</h1>") is None

    def test_empty(self):
        assert sanitize_url("") is None
        assert sanitize_url(None) is None

    def test_strips_whitespace(self):
        assert sanitize_url("  https://example.com  ") == "https://example.com"


class TestConstants:
    def test_expiry_map_values(self):
        assert EXPIRY_MAP["1h"] == 3600
        assert EXPIRY_MAP["24h"] == 86400
        assert EXPIRY_MAP["7d"] == 604800

    def test_max_expiry_is_4_months(self):
        assert MAX_EXPIRY == 10368000

    def test_data_ttl_is_6_months(self):
        assert DATA_TTL == 15552000
