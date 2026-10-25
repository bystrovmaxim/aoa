"""Tell an ordinary JWT refusal from a broken required-claim contract.
Run: uv run python examples/step_13_fastapi/09_required_claims.py

``JwtAuthenticator.authenticate`` has two kinds of "no":

* A token that fails verification -- bad signature, expired, wrong audience or
  issuer, no ``exp``, not a JWT at all -- returns ``None``. This check comes first,
  so a broken identifier inside such a token never raises.
* A token that passes verification but whose configured user-id claim (default
  ``sub``) or session claim is missing, null, empty, whitespace-only or not a
  string raises ``AuthenticationContractError``. The exception names the claim and
  the reason, never the value.

Every other string is accepted and carried exactly as written. A numeric ``sub``
is refused, not converted: the issuer must emit ``"12345"``, not ``12345``.

Over HTTP the two kinds stay apart: a refusal is ``403``, a contract failure is a
server error (``500``).

Requires:
    pip install "aoa-action-machine[jwt]" aoa-fastapi-adapter
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from fastapi.testclient import TestClient
from pydantic import Field

from aoa.action_machine.auth import ApplicationRole
from aoa.action_machine.auth.jwt_auth import JwtAuthCoordinator, JwtAuthenticator
from aoa.action_machine.context import ContextView, Ctx
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.exceptions import AuthenticationContractError
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.context_requires import context_requires
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseResult, ParamsStub
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.resources import Connections
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.action_machine.runtime.tools_box import ToolsBox
from aoa.fastapi import FastApiAdapter

_SECRET_KEY = "demo-only-secret-do-not-use-in-production"
_OTHER_KEY = "a-different-secret-the-service-does-not-trust"
_ALGORITHM = "HS256"

MISSING = object()  # marks a claim that is left out of the token


class AuthDomain(BaseDomain):
    name = "auth"
    description = "Authenticated session access"


class ViewerRole(ApplicationRole):
    name = "viewer"
    description = "Read-only access."


def token(*, key: str = _SECRET_KEY, expired: bool = False, **claims: Any) -> str:
    """Sign a token for alice in session-1; keyword arguments replace or remove claims."""
    now = datetime.now(UTC)
    exp = now - timedelta(minutes=1) if expired else now + timedelta(minutes=30)
    payload: dict[str, Any] = {"sub": "alice", "sid": "session-1", "roles": ["viewer"], "exp": exp}
    payload.update(claims)
    payload = {name: value for name, value in payload.items() if value is not MISSING}
    return jwt.encode(payload, key, algorithm=_ALGORITHM)


async def authenticate(authenticator: JwtAuthenticator, label: str, signed: str) -> Any:
    """Print what ``authenticate`` returns or raises, and hand the result back."""
    try:
        user = await authenticator.authenticate({"token": signed})
    except AuthenticationContractError as exc:
        print(f"{label:30} -> {type(exc).__name__}: {exc}")
        return exc
    shown = None if user is None else (user.user_id, user.session_id)
    print(f"{label:30} -> {shown!r}")
    return user


async def show_verification_comes_first(auth: JwtAuthenticator) -> None:
    """A token that fails verification is refused, whatever its identifiers look like."""
    assert await authenticate(auth, "signed with another key", token(key=_OTHER_KEY, sid="")) is None
    assert await authenticate(auth, "expired", token(expired=True, sub=12345)) is None
    assert await authenticate(auth, "no exp claim", token(exp=MISSING, sid=MISSING)) is None
    assert await authenticate(auth, "not a JWT", "not-a-jwt") is None


async def show_session_claim_contract(auth: JwtAuthenticator) -> None:
    """A verified token must carry a non-blank string session id."""
    for label, sid, reason in [
        ("sid missing", MISSING, "missing"),
        ("sid null", None, "missing"),
        ("sid empty", "", "empty"),
        ("sid whitespace-only", " \t\n", "whitespace-only"),
        ("sid not a string", 42, "not a string"),
    ]:
        error = await authenticate(auth, label, token(sid=sid))
        assert isinstance(error, AuthenticationContractError)
        assert (error.claim, error.reason) == ("sid", reason)

    # Any other string is opaque: no trimming, no case folding.
    user = await authenticate(auth, "sid ' Session-A '", token(sid=" Session-A "))
    assert user.session_id == " Session-A "


async def show_user_id_claim_contract(auth: JwtAuthenticator) -> None:
    """The user-id claim follows the same contract; a numeric sub is refused, not converted."""
    error = await authenticate(auth, "sub 12345 (number)", token(sub=12345))
    assert (error.claim, error.reason) == ("sub", "not a string")
    user = await authenticate(auth, "sub '12345' (string)", token(sub="12345"))
    assert user.user_id == "12345"
    error = await authenticate(auth, "sub missing", token(sub=MISSING))
    assert (error.claim, error.reason) == ("sub", "missing")

    # With a custom user_id_claim the error names that claim ...
    by_uid = JwtAuthenticator(secret_key=_SECRET_KEY, role_registry={"viewer": ViewerRole}, user_id_claim="uid", session_id_claim="sid")
    error = await authenticate(by_uid, "uid missing", token(sub=MISSING))
    assert (error.claim, error.reason) == ("uid", "missing")
    user = await authenticate(by_uid, "uid 'alice-01'", token(sub=MISSING, uid="alice-01"))
    assert user.user_id == "alice-01"
    # ... but a numeric registered sub is still refused, and the error names sub.
    error = await authenticate(by_uid, "uid ok, sub 12345 (number)", token(uid="alice-01", sub=12345))
    assert (error.claim, error.reason) == ("sub", "not a string")


class SessionResult(BaseResult):
    session_id: str = Field(description="Login session identifier")


@meta(description="Answer with the caller's session id.", domain=AuthDomain)
@check_roles(ViewerRole)
class SessionAction(BaseAction[ParamsStub, SessionResult]):

    @summary_aspect("Read the session id.")
    @context_requires(Ctx.User.session_id)
    async def session_summary(self, params: ParamsStub, state: BaseState, box: ToolsBox, connections: Connections, ctx: ContextView) -> SessionResult:
        return SessionResult(session_id=ctx.get(Ctx.User.session_id))


def show_http_answers() -> None:
    """Over FastAPI a refusal is 403 and a contract failure is a server error."""
    auth = JwtAuthCoordinator(secret_key=_SECRET_KEY, algorithm=_ALGORITHM, role_registry={"viewer": ViewerRole}, session_id_claim="sid")
    app = FastApiAdapter(machine=ActionProductMachine(), auth_coordinator=auth, title="Required Claims Demo").get("/session", SessionAction).build()
    client = TestClient(app, raise_server_exceptions=False)

    for label, signed, status in [
        ("valid token", token(), 200),
        ("expired token", token(expired=True), 403),
        ("verified token, sid empty", token(sid=""), 500),
    ]:
        response = client.get("/session", headers={"Authorization": f"Bearer {signed}"})
        request = f"GET /session ({label})"
        print(f"{request:40} -> {response.status_code} {response.json()}")
        assert response.status_code == status


async def main() -> None:
    auth = JwtAuthenticator(secret_key=_SECRET_KEY, role_registry={"viewer": ViewerRole}, session_id_claim="sid")

    print("-- 1. verification comes first")
    await show_verification_comes_first(auth)
    print("-- 2. the session claim")
    await show_session_claim_contract(auth)
    print("-- 3. the user-id claim")
    await show_user_id_claim_contract(auth)
    print("-- 4. the same tokens over HTTP")
    show_http_answers()


if __name__ == "__main__":
    asyncio.run(main())
