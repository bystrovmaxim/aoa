"""Base an access decision on the caller's session id.
Run: uv run python examples/step_13_fastapi/08_session_access_rule.py

AOA keeps no session store and has no logout. It carries the session id, and the
application decides what a session may do. Here the application keeps a registry
of ended sessions: ``LogoutAction`` records the caller's session in it, and the
``@access_decide`` rule of ``ListOrdersAction`` refuses a session found there.

The rule reads the session id the way an aspect does: it declares
``@context_requires(Ctx.User.session_id)`` and calls ``ctx.get(...)``. Ending one
session leaves the same user's other session working.

Requires:
    pip install "aoa-action-machine[jwt]" aoa-fastapi-adapter
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from itertools import count

import jwt
from fastapi.testclient import TestClient
from pydantic import Field

from aoa.action_machine.auth import ApplicationRole, GuestRole, NoAuthCoordinator
from aoa.action_machine.auth.jwt_auth import JwtAuthCoordinator
from aoa.action_machine.context import Context, ContextView, Ctx
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.access_control import Allowed, Refused, Verdict
from aoa.action_machine.intents.access_decide import access_decide
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.connection import connection
from aoa.action_machine.intents.context_requires import context_requires
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult, ParamsStub
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.resources import Connections
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.action_machine.runtime.tools_box import ToolsBox
from aoa.fastapi import FastApiAdapter

_SECRET_KEY = "demo-only-secret-do-not-use-in-production"
_ALGORITHM = "HS256"
_TOKEN_TTL = timedelta(minutes=30)

# A real issuer uses an unguessable random value; a counter keeps the output stable.
_session_numbers = count(1)


class OrdersDomain(BaseDomain):
    name = "orders"
    description = "Orders and the sessions that may read them"


class ViewerRole(ApplicationRole):
    name = "viewer"
    description = "Read-only access."


@meta(description="Application registry of ended login sessions.", domain=OrdersDomain)
class SessionRegistryResource(BaseResource):
    def __init__(self) -> None:
        self._ended: set[str] = set()

    def get_wrapper_class(self) -> type[BaseResource] | None:
        return None  # in-memory registry, no transaction to wrap

    async def end(self, session_id: str) -> None:
        self._ended.add(session_id)

    async def is_ended(self, session_id: str) -> bool:
        return session_id in self._ended


class LoginParams(BaseParams):
    username: str = Field(description="Account username")


class TokenResult(BaseResult):
    access_token: str = Field(description="Signed JWT bearer token")


class LogoutResult(BaseResult):
    ended_session: str = Field(description="Session that was ended")


class OrdersResult(BaseResult):
    orders: list[str] = Field(description="Order identifiers visible to the caller")


@meta(description="Start a new login session and issue its token.", domain=OrdersDomain)
@check_roles(GuestRole)
class LoginAction(BaseAction[LoginParams, TokenResult]):

    @summary_aspect("Sign a token with a new session id.")
    async def login_summary(self, params: LoginParams, state: BaseState, box: ToolsBox, connections: Connections) -> TokenResult:
        now = datetime.now(UTC)
        payload = {
            "sub": params.username,
            "sid": f"session-{next(_session_numbers)}",
            "roles": ["viewer"],
            "iat": now,
            "exp": now + _TOKEN_TTL,
        }
        return TokenResult(access_token=jwt.encode(payload, _SECRET_KEY, algorithm=_ALGORITHM))


@meta(description="End the caller's current login session.", domain=OrdersDomain)
@check_roles(ViewerRole)
@connection(SessionRegistryResource, key="sessions")
class LogoutAction(BaseAction[ParamsStub, LogoutResult]):

    @summary_aspect("Record the current session as ended.")
    @context_requires(Ctx.User.session_id)
    async def logout_summary(self, params: ParamsStub, state: BaseState, box: ToolsBox, connections: Connections, ctx: ContextView) -> LogoutResult:
        session_id = ctx.get(Ctx.User.session_id)
        await connections["sessions"].end(session_id)
        return LogoutResult(ended_session=session_id)


@meta(description="List orders for a caller whose session is still active.", domain=OrdersDomain)
@check_roles(ViewerRole)
@connection(SessionRegistryResource, key="sessions")
class ListOrdersAction(BaseAction[ParamsStub, OrdersResult]):

    @access_decide("Refuse a session the application has ended")
    @context_requires(Ctx.User.session_id)
    async def active_session_access_decide(self, params: ParamsStub, box: ToolsBox, connections: Connections, ctx: ContextView) -> Verdict:
        if await connections["sessions"].is_ended(ctx.get(Ctx.User.session_id)):
            return Refused("SESSION_ENDED")
        return Allowed()

    @summary_aspect("Return the caller's orders.")
    async def list_orders_summary(self, params: ParamsStub, state: BaseState, box: ToolsBox, connections: Connections) -> OrdersResult:
        return OrdersResult(orders=["ord-001"])


def build_app():
    registry = SessionRegistryResource()
    auth = JwtAuthCoordinator(
        secret_key=_SECRET_KEY,
        algorithm=_ALGORITHM,
        role_registry={"viewer": ViewerRole},
        session_id_claim="sid",
    )
    return (
        FastApiAdapter(machine=ActionProductMachine(), auth_coordinator=auth, title="Session Access Rule Demo")
        .post("/auth/login", LoginAction, auth_coordinator=NoAuthCoordinator(context=Context()))
        .post("/auth/logout", LogoutAction, connections={"sessions": registry})
        .get("/orders", ListOrdersAction, connections={"sessions": registry})
        .build()
    )


def main() -> None:
    client = TestClient(build_app(), raise_server_exceptions=False)

    def bearer(token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}

    laptop = client.post("/auth/login", json={"username": "alice"}).json()["access_token"]
    phone = client.post("/auth/login", json={"username": "alice"}).json()["access_token"]

    # 1. Both sessions are active: the rule allows both.
    before = client.get("/orders", headers=bearer(laptop))
    print(f"GET /orders (laptop, active)  -> {before.status_code} {before.json()}")
    assert before.status_code == 200

    # 2. The laptop session ends; the application records its session id.
    logout = client.post("/auth/logout", headers=bearer(laptop))
    print(f"POST /auth/logout (laptop)    -> {logout.status_code} {logout.json()}")
    assert logout.json() == {"ended_session": "session-1"}

    # 3. The laptop token is still signed and unexpired, but the rule refuses its session.
    after = client.get("/orders", headers=bearer(laptop))
    print(f"GET /orders (laptop, ended)   -> {after.status_code} {after.json()}")
    assert after.status_code == 403
    assert after.json() == {"detail": "Access denied by ACCESS_DECIDE: SESSION_ENDED"}

    # 4. The same user's other session is untouched.
    other = client.get("/orders", headers=bearer(phone))
    print(f"GET /orders (phone, active)   -> {other.status_code} {other.json()}")
    assert other.status_code == 200


if __name__ == "__main__":
    main()
