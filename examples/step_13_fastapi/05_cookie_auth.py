"""
05_cookie_auth.py — CookieCredentialExtractor: authenticate via an httpOnly session cookie.

The other JWT transport (see 03_login_action.py for issuing, 04_bearer_auth.py for
verifying via the Authorization header). This is same-site browser SSO: the login
route sets a `Set-Cookie: ...; HttpOnly` response, `CookieCredentialExtractor` reads
it back on later requests. The protected route below is never sent an Authorization
header at all -- the client (here, FastAPI's TestClient, which stores cookies exactly
like a browser) authenticates purely through the cookie the login route set. See
docs/extensions/jwt_draft.md#транспорт-заголовок-или-cookie for when cookie beats
header and vice versa.

Two things this example does differently from 04_bearer_auth.py, both because
JwtAuthCoordinator hard-codes BearerCredentialExtractor (there is a follow-up issue
to parameterize it):

  1. /auth/login is NOT registered through FastApiAdapter's .post() -- BaseResult has
     no field for response headers/cookies (Actions stay HTTP-agnostic by design), so
     there is no built-in way for an Action to set a Set-Cookie header. It is a plain
     FastAPI route that runs LoginAction through the machine directly -- the same
     "auth_coordinator.process -> resolve connections -> machine.run" pipeline every
     adapter follows -- then calls response.set_cookie() on the result.
  2. The adapter-wide auth_coordinator is assembled from AuthCoordinator directly:
     CookieCredentialExtractor + JwtAuthenticator + HttpContextAssembler -- the same
     three pieces JwtAuthCoordinator wires internally, with the extractor swapped.

Run from repository root:
    uv run python examples/step_13_fastapi/05_cookie_auth.py

Requires:
    pip install "aoa-action-machine[jwt]" aoa-fastapi-adapter
"""

from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Response
from fastapi.testclient import TestClient
from pydantic import Field

from aoa.action_machine.auth import ApplicationRole, AuthCoordinator, GuestRole, NoAuthCoordinator
from aoa.action_machine.auth.jwt_auth import CookieCredentialExtractor, HttpContextAssembler, JwtAuthenticator
from aoa.action_machine.context import Context
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.exceptions import AuthorizationError
from aoa.action_machine.intents.aspects import regular_aspect, summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.checkers import result_instance, result_string
from aoa.action_machine.intents.connection import connection
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult, ParamsStub
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.resources.per_call_connection import resolve_connections
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.fastapi import FastApiAdapter

# --- Signing config (shared by LoginAction and the cookie-reading coordinator --
# secret_key/algorithm MUST match between whoever signs and whoever verifies) ---
_SECRET_KEY = "demo-only-secret-do-not-use-in-production"
_ALGORITHM = "HS256"
_TOKEN_TTL = timedelta(minutes=30)
_COOKIE_NAME = "session"


class AuthDomain(BaseDomain):
    name = "auth"
    description = "Login and token issuance"


class OrdersDomain(BaseDomain):
    name = "orders"
    description = "Order management -- requires authentication"


class AdminRole(ApplicationRole):
    name = "admin"
    description = "Full administrative access."


@meta(description="Transport to the user credential store.", domain=AuthDomain)
class UserStoreResource(BaseResource):
    def __init__(self, users: dict[str, tuple[str, list[str]]]) -> None:
        self._users = users

    def get_wrapper_class(self) -> type[BaseResource] | None:
        return None  # simple non-transactional resource, no nested-call restrictions

    async def find(self, username: str) -> tuple[str, list[str]] | None:
        return self._users.get(username)


# Fake user store: username -> (password, role names). See 03_login_action.py.
# Wired to LoginAction via @connection, not read directly.
_USER_STORE: dict[str, tuple[str, list[str]]] = {
    "alice": ("wonderland", ["admin"]),
}


class LoginParams(BaseParams):
    username: str = Field(description="Account username")
    password: str = Field(description="Account password")


class LoginResult(BaseResult):
    access_token: str = Field(description="Signed JWT -- set as an httpOnly cookie below, never returned to JS")
    expires_in: int = Field(description="Token lifetime in seconds")


@meta(description="Authenticate a username/password pair and issue a JWT.", domain=AuthDomain)
@check_roles(GuestRole)
@connection(UserStoreResource, key="user_store")
class LoginAction(BaseAction[LoginParams, LoginResult]):

    @result_string("user_id", required=True, not_empty=True)  # type: ignore[untyped-decorator]
    @result_instance("role_names", list, required=True)  # type: ignore[untyped-decorator]
    @regular_aspect("Verify username/password against the user store; resolve role names.")
    async def authenticate_user_aspect(self, params: LoginParams, state, box, connections) -> dict:
        _ = (state, box)
        store: UserStoreResource = connections["user_store"]
        record = await store.find(params.username)
        if record is None or record[0] != params.password:
            raise AuthorizationError("Invalid username or password")
        _password, role_names = record
        return {"user_id": params.username, "role_names": role_names}

    @summary_aspect("Sign a JWT carrying sub (user_id) and roles.")
    async def issue_token_summary(self, params: LoginParams, state, box, connections) -> LoginResult:
        _ = (params, box, connections)
        now = datetime.now(UTC)
        payload = {
            "sub": state["user_id"],
            "roles": state["role_names"],
            "iat": now,
            "exp": now + _TOKEN_TTL,
        }
        token = jwt.encode(payload, _SECRET_KEY, algorithm=_ALGORITHM)
        return LoginResult(access_token=token, expires_in=int(_TOKEN_TTL.total_seconds()))


class OrderSummaryResult(BaseResult):
    message: str = Field(description="Confirmation the caller reached a protected route")


@meta(description="A protected route -- only reachable with a valid admin session cookie.", domain=OrdersDomain)
@check_roles(AdminRole)
class ListOrdersAction(BaseAction[ParamsStub, OrderSummaryResult]):

    @summary_aspect("Return a fixed confirmation message.")
    async def build_summary(self, params, state, box, connections) -> OrderSummaryResult:
        _ = (params, state, box, connections)
        return OrderSummaryResult(
            message="orders: [] -- reached with a valid admin session cookie, no Authorization header sent"
        )


def build_app():
    machine = ActionProductMachine()

    # No JwtAuthCoordinator here -- it hard-codes BearerCredentialExtractor. Assemble
    # AuthCoordinator directly with the same three pieces JwtAuthCoordinator would use
    # internally, swapping in CookieCredentialExtractor for the extractor.
    cookie_auth = AuthCoordinator(
        extractor=CookieCredentialExtractor(cookie_name=_COOKIE_NAME),
        auth_instance=JwtAuthenticator(
            secret_key=_SECRET_KEY,
            algorithm=_ALGORITHM,
            role_registry={"admin": AdminRole},
        ),
        assembler=HttpContextAssembler(),
    )

    fastapi_app = (
        FastApiAdapter(machine=machine, auth_coordinator=cookie_auth, title="Cookie Auth Demo")
        .get("/orders", ListOrdersAction, tags=["orders"])
        .build()
    )

    # /auth/login sets a response cookie -- Actions/BaseResult have no hook for that, so
    # this route is hand-written FastAPI running the same "auth -> connections -> machine.run"
    # pipeline every adapter follows, then response.set_cookie() on the result.
    login_connections = {"user_store": UserStoreResource(_USER_STORE)}

    @fastapi_app.post("/auth/login", tags=["auth"])
    async def login(params: LoginParams, response: Response) -> dict[str, str]:
        context = await NoAuthCoordinator(context=Context()).process(None)
        connections = resolve_connections(login_connections)
        result = await machine.run(context, LoginAction(), params, connections)
        response.set_cookie(
            key=_COOKIE_NAME,
            value=result.access_token,
            httponly=True,
            samesite="lax",
            max_age=result.expires_in,
        )
        return {"status": "logged in"}

    return fastapi_app


def main() -> None:
    client = TestClient(build_app(), raise_server_exceptions=False)

    # 1. No cookie at all -> denied -> 403. No Authorization header exists in this demo.
    no_cookie = client.get("/orders")
    print(f"GET /orders (no cookie)          -> {no_cookie.status_code} {no_cookie.json()}")

    # 2. Log in -> the response sets an httpOnly session cookie; TestClient stores it
    #    automatically, exactly like a browser would.
    login = client.post("/auth/login", json={"username": "alice", "password": "wonderland"})
    print(f"POST /auth/login                 -> {login.status_code} {login.json()}")

    # 3. Same client, no Authorization header anywhere -> the stored cookie authenticates.
    ok = client.get("/orders")
    print(f"GET /orders (cookie, no header)  -> {ok.status_code} {ok.json()}")

    # 4. Drop the cookie -> back to denied, same as step 1.
    client.cookies.clear()
    dropped = client.get("/orders")
    print(f"GET /orders (cookie cleared)     -> {dropped.status_code} {dropped.json()}")


if __name__ == "__main__":
    main()
