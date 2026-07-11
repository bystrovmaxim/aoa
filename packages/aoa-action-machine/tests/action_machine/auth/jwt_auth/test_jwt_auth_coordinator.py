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
from unittest.mock import Mock

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from aoa.action_machine.auth.auth_coordinator import ContextAssembler, CredentialExtractor
from aoa.action_machine.auth.base_role import BaseRole
from aoa.action_machine.auth.jwt_auth.bearer_credential_extractor import BearerCredentialExtractor
from aoa.action_machine.auth.jwt_auth.cookie_credential_extractor import CookieCredentialExtractor
from aoa.action_machine.auth.jwt_auth.jwt_auth_coordinator import JwtAuthCoordinator
from aoa.action_machine.intents.role_mode.role_mode_decorator import RoleMode, role_mode

_SECRET = "unit-test-secret-key-not-for-production-use"
_JWKS_URL = "https://issuer.example.com/.well-known/jwks.json"


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
    def __init__(
        self,
        *,
        headers: dict[str, str] | None = None,
        cookies: dict[str, str] | None = None,
        path: str = "/orders",
    ) -> None:
        self.headers = headers or {}
        self.cookies = cookies or {}
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


async def test_default_credential_extractor_is_bearer() -> None:
    coordinator = _make_coordinator()

    assert isinstance(coordinator.extractor, BearerCredentialExtractor)


async def test_custom_credential_extractor_is_used_instead_of_default() -> None:
    token = _sign()

    class _StubExtractor(CredentialExtractor):
        async def extract(self, request_data: Any) -> dict[str, Any]:
            _ = request_data
            return {"token": token}

    coordinator = _make_coordinator(credential_extractor=_StubExtractor())

    # No Authorization header at all -- the stub supplies the token instead of Bearer.
    context = await coordinator.process(_FakeRequest())

    assert context is not None
    assert context.user.user_id == "alice"


async def test_cookie_credential_extractor_produces_populated_context() -> None:
    token = _sign()
    coordinator = _make_coordinator(credential_extractor=CookieCredentialExtractor(cookie_name="session"))

    context = await coordinator.process(_FakeRequest(cookies={"session": token}, path="/api/v1/orders"))

    assert context is not None
    assert context.user.user_id == "alice"
    assert context.user.roles == (AdminRole,)
    assert context.request.request_path == "/api/v1/orders"
    assert context.request.protocol == "http"


def test_both_secret_key_and_jwks_url_raises_value_error_through_coordinator() -> None:
    """JwtAuthCoordinator forwards secret_key/jwks_url as-is -- the XOR check fires through the wrapper too."""
    with pytest.raises(ValueError, match="exactly one"):
        JwtAuthCoordinator(secret_key=_SECRET, jwks_url=_JWKS_URL, role_registry={"admin": AdminRole})


def test_neither_secret_key_nor_jwks_url_raises_value_error_through_coordinator() -> None:
    with pytest.raises(ValueError, match="exactly one"):
        JwtAuthCoordinator(role_registry={"admin": AdminRole})


async def test_jwks_url_produces_populated_context_through_coordinator() -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()

    coordinator = _make_coordinator(secret_key=None, jwks_url=_JWKS_URL, algorithm="RS256")
    coordinator.authenticator._jwks_client = Mock(  # type: ignore[attr-defined]
        get_signing_key_from_jwt=Mock(return_value=Mock(key=private_key.public_key())),
    )
    now = datetime.now(UTC)
    token = jwt.encode(
        {"sub": "alice", "roles": ["admin"], "iat": now, "exp": now + timedelta(minutes=30)},
        private_pem,
        algorithm="RS256",
        headers={"kid": "test-kid-1"},
    )

    context = await coordinator.process(_FakeRequest(headers={"authorization": f"Bearer {token}"}))

    assert context is not None
    assert context.user.user_id == "alice"
    assert context.user.roles == (AdminRole,)
