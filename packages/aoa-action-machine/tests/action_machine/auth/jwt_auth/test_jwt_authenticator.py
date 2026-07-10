# tests/auth/jwt_auth/test_jwt_authenticator.py
"""Tests for JwtAuthenticator — verify a JWT and resolve claims to UserInfo."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from aoa.action_machine.auth.base_role import BaseRole
from aoa.action_machine.auth.jwt_auth.jwt_authenticator import JwtAuthenticator
from aoa.action_machine.intents.role_mode.role_mode_decorator import RoleMode, role_mode

_SECRET = "unit-test-secret-key-not-for-production-use"
_ALGORITHM = "HS256"


# @role_mode is mandatory here, not optional decoration: the coordinator graph
# walks *every* BaseRole subclass alive in the process (pytest imports all test
# modules into one shared process), and chokes on any role missing _role_mode_info.
@role_mode(RoleMode.ALIVE)
class AdminRole(BaseRole):
    name = "admin"
    description = "Full access."


@role_mode(RoleMode.ALIVE)
class ViewerRole(BaseRole):
    name = "viewer"
    description = "Read-only access."


def _sign(payload: dict[str, Any], *, secret: str = _SECRET, algorithm: str = _ALGORITHM) -> str:
    return jwt.encode(payload, secret, algorithm=algorithm)


def _valid_payload(**overrides: Any) -> dict[str, Any]:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": "alice",
        "roles": ["admin"],
        "iat": now,
        "exp": now + timedelta(minutes=30),
    }
    payload.update(overrides)
    return payload


def _make_authenticator(**overrides: Any) -> JwtAuthenticator:
    kwargs: dict[str, Any] = {
        "secret_key": _SECRET,
        "algorithm": _ALGORITHM,
        "role_registry": {"admin": AdminRole, "viewer": ViewerRole},
    }
    kwargs.update(overrides)
    return JwtAuthenticator(**kwargs)


# ═════════════════════════════════════════════════════════════════════════════
# Success
# ═════════════════════════════════════════════════════════════════════════════


async def test_valid_token_resolves_user_id_and_roles() -> None:
    authenticator = _make_authenticator()
    token = _sign(_valid_payload())

    result = await authenticator.authenticate({"token": token})

    assert result is not None
    assert result.user_id == "alice"
    assert result.roles == (AdminRole,)


async def test_multiple_roles_all_mapped() -> None:
    authenticator = _make_authenticator()
    token = _sign(_valid_payload(roles=["admin", "viewer"]))

    result = await authenticator.authenticate({"token": token})

    assert result is not None
    assert set(result.roles) == {AdminRole, ViewerRole}


async def test_unmapped_role_names_are_dropped_not_rejected() -> None:
    authenticator = _make_authenticator()
    token = _sign(_valid_payload(roles=["admin", "some_unknown_role"]))

    result = await authenticator.authenticate({"token": token})

    assert result is not None
    assert result.roles == (AdminRole,)


async def test_malformed_roles_claim_yields_empty_roles_not_failure() -> None:
    authenticator = _make_authenticator()
    token = _sign(_valid_payload(roles="not-a-list"))

    result = await authenticator.authenticate({"token": token})

    assert result is not None
    assert result.roles == ()


async def test_missing_roles_claim_yields_empty_roles() -> None:
    authenticator = _make_authenticator()
    payload = _valid_payload()
    del payload["roles"]
    token = _sign(payload)

    result = await authenticator.authenticate({"token": token})

    assert result is not None
    assert result.roles == ()


async def test_custom_claim_names() -> None:
    authenticator = _make_authenticator(user_id_claim="user_id", roles_claim="perms")
    now = datetime.now(UTC)
    token = _sign({"user_id": "bob", "perms": ["viewer"], "iat": now, "exp": now + timedelta(minutes=5)})

    result = await authenticator.authenticate({"token": token})

    assert result is not None
    assert result.user_id == "bob"
    assert result.roles == (ViewerRole,)


async def test_matching_audience_succeeds() -> None:
    authenticator = _make_authenticator(audience="my-api")
    token = _sign(_valid_payload(aud="my-api"))

    result = await authenticator.authenticate({"token": token})

    assert result is not None


# ═════════════════════════════════════════════════════════════════════════════
# Failure -> None, never raises
# ═════════════════════════════════════════════════════════════════════════════


async def test_no_token_in_credentials_returns_none() -> None:
    authenticator = _make_authenticator()
    assert await authenticator.authenticate({}) is None


async def test_expired_token_returns_none() -> None:
    authenticator = _make_authenticator()
    past = datetime.now(UTC) - timedelta(minutes=5)
    token = _sign(_valid_payload(iat=past - timedelta(minutes=30), exp=past))

    assert await authenticator.authenticate({"token": token}) is None


async def test_wrong_secret_key_returns_none() -> None:
    authenticator = _make_authenticator()
    token = _sign(_valid_payload(), secret="a-completely-different-unit-test-secret-key")

    assert await authenticator.authenticate({"token": token}) is None


async def test_wrong_algorithm_returns_none() -> None:
    authenticator = _make_authenticator(algorithm="HS256")
    token = _sign(_valid_payload(), secret=_SECRET + "-padded-for-hs384-min-key-length", algorithm="HS384")

    assert await authenticator.authenticate({"token": token}) is None


async def test_wrong_audience_returns_none() -> None:
    authenticator = _make_authenticator(audience="my-api")
    token = _sign(_valid_payload(aud="a-different-api"))

    assert await authenticator.authenticate({"token": token}) is None


async def test_missing_user_id_claim_returns_none() -> None:
    authenticator = _make_authenticator()
    payload = _valid_payload()
    del payload["sub"]
    token = _sign(payload)

    assert await authenticator.authenticate({"token": token}) is None


async def test_missing_exp_claim_returns_none() -> None:
    """Expiry is mandatory -- a token that never expires is rejected outright."""
    authenticator = _make_authenticator()
    payload = _valid_payload()
    del payload["exp"]
    token = _sign(payload)

    assert await authenticator.authenticate({"token": token}) is None


async def test_malformed_token_returns_none() -> None:
    authenticator = _make_authenticator()
    assert await authenticator.authenticate({"token": "not-a-jwt-at-all"}) is None
