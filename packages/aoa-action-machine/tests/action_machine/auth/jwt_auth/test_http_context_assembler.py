# tests/auth/jwt_auth/test_http_context_assembler.py
"""Tests for HttpContextAssembler — RequestInfo kwargs from an HTTP-shaped request."""

from __future__ import annotations

from typing import Any

from aoa.action_machine.auth.jwt_auth.http_context_assembler import HttpContextAssembler
from aoa.action_machine.context.request_info import RequestInfo

_ASSEMBLER = HttpContextAssembler()


class _FakeUrl:
    def __init__(self, path: str, full: str) -> None:
        self.path = path
        self._full = full

    def __str__(self) -> str:
        return self._full


class _FakeClient:
    def __init__(self, host: str) -> None:
        self.host = host


class _FakeRequest:
    """Minimal stand-in for a Starlette ``Request`` — ``.url.path``, not ``.path``."""

    def __init__(
        self,
        *,
        path: str = "/orders",
        full_url: str = "http://testserver/orders",
        method: str = "GET",
        headers: dict[str, str] | None = None,
        client: Any = None,
    ) -> None:
        self.url = _FakeUrl(path, full_url)
        self.method = method
        self.headers = headers or {}
        self.client = client


async def test_assembles_path_method_and_url() -> None:
    result = await _ASSEMBLER.assemble(_FakeRequest())
    assert result["request_path"] == "/orders"
    assert result["request_method"] == "GET"
    assert result["full_url"] == "http://testserver/orders"
    assert result["protocol"] == "http"


async def test_reads_trace_id_header_when_present() -> None:
    result = await _ASSEMBLER.assemble(_FakeRequest(headers={"x-trace-id": "trace-42"}))
    assert result["trace_id"] == "trace-42"


async def test_trace_id_absent_is_none() -> None:
    result = await _ASSEMBLER.assemble(_FakeRequest())
    assert result["trace_id"] is None


async def test_client_ip_from_client_host() -> None:
    result = await _ASSEMBLER.assemble(_FakeRequest(client=_FakeClient("10.0.0.5")))
    assert result["client_ip"] == "10.0.0.5"


async def test_client_ip_none_when_no_client() -> None:
    result = await _ASSEMBLER.assemble(_FakeRequest(client=None))
    assert result["client_ip"] is None


async def test_result_matches_request_info_field_names() -> None:
    """Every key the assembler emits must be a valid RequestInfo field (extra='forbid')."""
    result = await _ASSEMBLER.assemble(_FakeRequest())
    RequestInfo(**result)
