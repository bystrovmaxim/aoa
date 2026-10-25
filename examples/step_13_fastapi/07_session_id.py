"""Configure the JWT session claim and read the session id in an aspect.
Run: uv run python examples/step_13_fastapi/07_session_id.py

A JWT authenticated by ``JwtAuthCoordinator`` identifies the caller (``sub``) and
the login session (here the ``sid`` claim). ``session_id_claim`` is a required
constructor argument: the coordinator refuses to be built without it.

The session id reaches an Action like any other context field: an aspect declares
``@context_requires(Ctx.User.session_id)`` and reads ``ctx.get(Ctx.User.session_id)``.

The token issuer owns the session lifecycle. In this example the issuer is the
service itself: every login gets a new session id, and a refresh signs a fresh
token that keeps the session id of the token it replaces.

Requires:
    pip install "aoa-action-machine[jwt]" aoa-fastapi-adapter
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from itertools import count
from uuid import uuid4

import jwt
from fastapi.testclient import TestClient
from pydantic import Field

from aoa.action_machine.auth import ApplicationRole, GuestRole, NoAuthCoordinator
from aoa.action_machine.auth.jwt_auth import JwtAuthCoordinator
from aoa.action_machine.context import Context, ContextView, Ctx
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.context_requires import context_requires
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult, ParamsStub
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.resources import Connections
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.action_machine.runtime.tools_box import ToolsBox
from aoa.fastapi import FastApiAdapter

_SECRET_KEY = "demo-only-secret-do-not-use-in-production"
_ALGORITHM = "HS256"
_TOKEN_TTL = timedelta(minutes=30)

# A real issuer uses an unguessable random value (for example secrets.token_urlsafe()).
# A counter keeps this example's output stable.
_session_numbers = count(1)


class AuthDomain(BaseDomain):
    name = "auth"
    description = "Login, refresh and identity"


class ViewerRole(ApplicationRole):
    name = "viewer"
    description = "Read-only access."


def _sign(user_id: str, session_id: str) -> str:
    """Sign a token for one caller in one login session; ``jti`` identifies the token itself."""
    now = datetime.now(UTC)
    payload = {"sub": user_id, "sid": session_id, "jti": uuid4().hex, "roles": ["viewer"], "iat": now, "exp": now + _TOKEN_TTL}
    return jwt.encode(payload, _SECRET_KEY, algorithm=_ALGORITHM)


class LoginParams(BaseParams):
    username: str = Field(description="Account username")


class TokenResult(BaseResult):
    access_token: str = Field(description="Signed JWT bearer token")


class IdentityResult(BaseResult):
    user_id: str = Field(description="Caller identifier from the token")
    session_id: str = Field(description="Login session identifier from the token")


@meta(description="Start a new login session and issue its first token.", domain=AuthDomain)
@check_roles(GuestRole)
class LoginAction(BaseAction[LoginParams, TokenResult]):

    @summary_aspect("Sign a token with a new session id.")
    async def login_summary(self, params: LoginParams, state: BaseState, box: ToolsBox, connections: Connections) -> TokenResult:
        session_id = f"session-{next(_session_numbers)}"
        return TokenResult(access_token=_sign(params.username, session_id))


@meta(description="Issue a fresh token for the current login session.", domain=AuthDomain)
@check_roles(ViewerRole)
class RefreshAction(BaseAction[ParamsStub, TokenResult]):

    @summary_aspect("Sign a fresh token that keeps the session id.")
    @context_requires(Ctx.User.user_id, Ctx.User.session_id)
    async def refresh_summary(self, params: ParamsStub, state: BaseState, box: ToolsBox, connections: Connections, ctx: ContextView) -> TokenResult:
        return TokenResult(access_token=_sign(ctx.get(Ctx.User.user_id), ctx.get(Ctx.User.session_id)))


@meta(description="Report who is calling and from which session.", domain=AuthDomain)
@check_roles(ViewerRole)
class WhoAmIAction(BaseAction[ParamsStub, IdentityResult]):

    @summary_aspect("Read the caller and the session from the context.")
    @context_requires(Ctx.User.user_id, Ctx.User.session_id)
    async def whoami_summary(self, params: ParamsStub, state: BaseState, box: ToolsBox, connections: Connections, ctx: ContextView) -> IdentityResult:
        return IdentityResult(user_id=ctx.get(Ctx.User.user_id), session_id=ctx.get(Ctx.User.session_id))


def show_configuration_rules() -> None:
    """The session claim name is required and must be a non-empty string."""
    try:
        JwtAuthCoordinator(secret_key=_SECRET_KEY, role_registry={"viewer": ViewerRole})
        raise AssertionError("a coordinator without session_id_claim must not be built")
    except TypeError as exc:
        print(f"no session_id_claim  -> {type(exc).__name__}: {exc}")
        assert "session_id_claim" in str(exc)

    try:
        JwtAuthCoordinator(secret_key=_SECRET_KEY, role_registry={"viewer": ViewerRole}, session_id_claim="")
        raise AssertionError("an empty session_id_claim must be refused")
    except ValueError as exc:
        print(f"session_id_claim=''  -> {type(exc).__name__}: {exc}")
        assert str(exc) == "session_id_claim must be a non-empty string; got ''."


def build_app():
    auth = JwtAuthCoordinator(
        secret_key=_SECRET_KEY,
        algorithm=_ALGORITHM,
        role_registry={"viewer": ViewerRole},
        session_id_claim="sid",
    )
    return (
        FastApiAdapter(machine=ActionProductMachine(), auth_coordinator=auth, title="Session Id Demo")
        # Login has no token to present yet, so it opts out of the JWT default.
        .post("/auth/login", LoginAction, auth_coordinator=NoAuthCoordinator(context=Context()))
        .post("/auth/refresh", RefreshAction)
        .get("/me", WhoAmIAction)
        .build()
    )


def main() -> None:
    show_configuration_rules()

    client = TestClient(build_app(), raise_server_exceptions=False)

    def login(username: str) -> str:
        return client.post("/auth/login", json={"username": username}).json()["access_token"]

    def whoami(token: str) -> dict[str, str]:
        response = client.get("/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200, response.text
        return response.json()

    # Two logins of one user are two sessions.
    laptop = login("alice")
    phone = login("alice")
    print(f"GET /me (laptop token)    -> {whoami(laptop)}")
    print(f"GET /me (phone token)     -> {whoami(phone)}")
    assert whoami(laptop) == {"user_id": "alice", "session_id": "session-1"}
    assert whoami(phone) == {"user_id": "alice", "session_id": "session-2"}

    # A refresh issues a new token inside the same session.
    refreshed = client.post("/auth/refresh", headers={"Authorization": f"Bearer {laptop}"}).json()["access_token"]
    print(f"refreshed token is new    -> {refreshed != laptop}")
    print(f"GET /me (refreshed token) -> {whoami(refreshed)}")
    assert refreshed != laptop
    assert whoami(refreshed) == whoami(laptop)


if __name__ == "__main__":
    main()
