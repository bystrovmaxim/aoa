# tests/auth/jwt_auth/test_jwt_auth_coordinator.py
"""
Tests for JwtAuthCoordinator — the full extract -> authenticate -> assemble -> Context
pipeline, assembled from BearerCredentialExtractor + JwtAuthenticator + HttpContextAssembler.

FastAPI-level end-to-end proof (a real app, a real LoginAction-issued token, a
real protected route) lives in ``examples/step_13_fastapi/04_bearer_auth.py`` —
aoa-action-machine's own test suite has no FastAPI dependency and stays
protocol-agnostic, exercising the coordinator against a duck-typed fake request.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from aoa.action_machine.auth.auth_coordinator import ContextAssembler
from aoa.action_machine.auth.base_role import BaseRole
from aoa.action_machine.auth.jwt_auth.jwt_auth_coordinator import JwtAuthCoordinator
from aoa.action_machine.intents.role_mode.role_mode_decorator import RoleMode, role_mode

_SECRET = "unit-test-secret-key-not-for-production-use"


# @role_mode is mandatory here, not optional decoration: the coordinator graph
# walks *every* BaseRole subclass alive in the process (pytest imports all test
# modules into one shared process), and chokes on any role missing _role_mode_info.
@role_mode(RoleMode.ALIVE)
class AdminRole(BaseRole):
    name = "admin"
    description = "Full access."


class _FakeUrl:
    def __init__(self, path: str) -> None:
        self.path = path

    def __str__(self) -> str:
        return f"http://testserver{self.path}"


class _FakeRequest:
    def __init__(self, *, headers: dict[str, str] | None = None, path: str = "/orders") -> None:
        self.headers = headers or {}
        self.url = _FakeUrl(path)
        self.method = "GET"
        self.client = None


def _sign(**overrides: Any) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {"sub": "alice", "roles": ["admin"], "iat": now, "exp": now + timedelta(minutes=30)}
    payload.update(overrides)
    return jwt.encode(payload, _SECRET, algorithm="HS256")


def _make_coordinator(**overrides: Any) -> JwtAuthCoordinator:
    kwargs: dict[str, Any] = {"secret_key": _SECRET, "role_registry": {"admin": AdminRole}}
    kwargs.update(overrides)
    return JwtAuthCoordinator(**kwargs)


async def test_valid_bearer_token_produces_populated_context() -> None:
    coordinator = _make_coordinator()
    token = _sign()

    context = await coordinator.process(_FakeRequest(headers={"authorization": f"Bearer {token}"}))

    assert context is not None
    assert context.user.user_id == "alice"
    assert context.user.roles == (AdminRole,)


async def test_missing_header_returns_none() -> None:
    coordinator = _make_coordinator()

    assert await coordinator.process(_FakeRequest()) is None


async def test_invalid_token_returns_none() -> None:
    coordinator = _make_coordinator()

    result = await coordinator.process(_FakeRequest(headers={"authorization": "Bearer garbage"}))

    assert result is None


async def test_expired_token_returns_none() -> None:
    coordinator = _make_coordinator()
    past = datetime.now(UTC) - timedelta(minutes=1)
    token = _sign(iat=past - timedelta(minutes=30), exp=past)

    result = await coordinator.process(_FakeRequest(headers={"authorization": f"Bearer {token}"}))

    assert result is None


async def test_default_assembler_populates_request_info() -> None:
    coordinator = _make_coordinator()
    token = _sign()

    context = await coordinator.process(
        _FakeRequest(headers={"authorization": f"Bearer {token}"}, path="/api/v1/orders"),
    )

    assert context is not None
    assert context.request.request_path == "/api/v1/orders"
    assert context.request.protocol == "http"


async def test_custom_context_assembler_is_used_instead_of_default() -> None:
    class _StubAssembler(ContextAssembler):
        async def assemble(self, request_data: Any) -> dict[str, Any]:
            _ = request_data
            return {"trace_id": "fixed-trace-id"}

    coordinator = _make_coordinator(context_assembler=_StubAssembler())
    token = _sign()

    context = await coordinator.process(_FakeRequest(headers={"authorization": f"Bearer {token}"}))

    assert context is not None
    assert context.request.trace_id == "fixed-trace-id"
    assert context.request.request_path is None  # the stub never set it
