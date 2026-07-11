# tests/auth/jwt_auth/test_cookie_credential_extractor.py
"""Tests for CookieCredentialExtractor — pulls a JWT out of a named HTTP cookie."""

from __future__ import annotations

import pytest

from aoa.action_machine.auth.jwt_auth.cookie_credential_extractor import CookieCredentialExtractor

_EXTRACTOR = CookieCredentialExtractor(cookie_name="session")


class _FakeRequest:
    """Minimal stand-in exposing only the ``.cookies`` mapping the extractor reads."""

    def __init__(self, cookies: dict[str, str]) -> None:
        self.cookies = cookies


async def test_extracts_token_from_configured_cookie() -> None:
    result = await _EXTRACTOR.extract(_FakeRequest({"session": "abc.def.ghi"}))
    assert result == {"token": "abc.def.ghi"}


async def test_cookie_missing_returns_empty_dict() -> None:
    result = await _EXTRACTOR.extract(_FakeRequest({}))
    assert result == {}


async def test_empty_cookie_value_returns_empty_dict() -> None:
    result = await _EXTRACTOR.extract(_FakeRequest({"session": ""}))
    assert result == {}


async def test_whitespace_only_cookie_value_returns_empty_dict() -> None:
    result = await _EXTRACTOR.extract(_FakeRequest({"session": "   "}))
    assert result == {}


async def test_other_cookies_present_target_absent_returns_empty_dict() -> None:
    result = await _EXTRACTOR.extract(_FakeRequest({"other": "value", "unrelated": "abc"}))
    assert result == {}


async def test_token_is_stripped_of_surrounding_whitespace() -> None:
    result = await _EXTRACTOR.extract(_FakeRequest({"session": "  abc.def.ghi  "}))
    assert result == {"token": "abc.def.ghi"}


async def test_cookie_name_is_case_sensitive() -> None:
    result = await _EXTRACTOR.extract(_FakeRequest({"Session": "abc.def.ghi"}))
    assert result == {}


async def test_requires_cookie_name_at_construction() -> None:
    with pytest.raises(TypeError):
        CookieCredentialExtractor()  # type: ignore[call-arg]


async def test_request_data_with_no_cookies_attribute_raises_type_error() -> None:
    """A wiring error (e.g. McpAdapter's process(None)) -- not a missing-credentials case."""
    with pytest.raises(TypeError, match="requires request_data exposing"):
        await _EXTRACTOR.extract(None)


async def test_request_data_missing_cookies_attribute_raises_type_error() -> None:
    class _NoCookies:
        pass

    with pytest.raises(TypeError, match="requires request_data exposing"):
        await _EXTRACTOR.extract(_NoCookies())
