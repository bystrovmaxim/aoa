# tests/auth/jwt_auth/test_bearer_credential_extractor.py
"""Tests for BearerCredentialExtractor — pulls a Bearer token out of Authorization."""

from __future__ import annotations

import pytest

from aoa.action_machine.auth.jwt_auth.bearer_credential_extractor import BearerCredentialExtractor

_EXTRACTOR = BearerCredentialExtractor()


class _FakeRequest:
    """Minimal stand-in exposing only the ``.headers`` mapping the extractor reads."""

    def __init__(self, headers: dict[str, str]) -> None:
        self.headers = headers


async def test_extracts_token_from_bearer_header() -> None:
    result = await _EXTRACTOR.extract(_FakeRequest({"authorization": "Bearer abc.def.ghi"}))
    assert result == {"token": "abc.def.ghi"}


async def test_scheme_is_case_insensitive() -> None:
    result = await _EXTRACTOR.extract(_FakeRequest({"authorization": "bearer abc.def.ghi"}))
    assert result == {"token": "abc.def.ghi"}


async def test_missing_header_returns_empty_dict() -> None:
    result = await _EXTRACTOR.extract(_FakeRequest({}))
    assert result == {}


async def test_wrong_scheme_returns_empty_dict() -> None:
    result = await _EXTRACTOR.extract(_FakeRequest({"authorization": "Basic dXNlcjpwYXNz"}))
    assert result == {}


async def test_empty_token_after_scheme_returns_empty_dict() -> None:
    result = await _EXTRACTOR.extract(_FakeRequest({"authorization": "Bearer   "}))
    assert result == {}


async def test_scheme_with_no_token_returns_empty_dict() -> None:
    result = await _EXTRACTOR.extract(_FakeRequest({"authorization": "Bearer"}))
    assert result == {}


async def test_empty_header_value_returns_empty_dict() -> None:
    result = await _EXTRACTOR.extract(_FakeRequest({"authorization": ""}))
    assert result == {}


async def test_request_data_with_no_headers_attribute_raises_type_error() -> None:
    """A wiring error (e.g. McpAdapter's process(None)) -- not a missing-credentials case."""
    with pytest.raises(TypeError, match="requires request_data exposing"):
        await _EXTRACTOR.extract(None)


async def test_request_data_missing_headers_attribute_raises_type_error() -> None:
    class _NoHeaders:
        pass

    with pytest.raises(TypeError, match="requires request_data exposing"):
        await _EXTRACTOR.extract(_NoHeaders())
