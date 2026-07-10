"""
04_bearer_auth.py — JwtAuthCoordinator: verify Bearer tokens on every request.

The second half of JWT authentication (see 03_login_action.py for the first
half -- signing). LoginAction issues a token; JwtAuthCoordinator verifies it on
every subsequent request. Here it is the FastAPI adapter's strict default
coordinator, with an explicit per-route exception for /auth/login (which has
no token to present) -- the same override mechanism from 02_auth_override.py.

Run from repository root:
    uv run python examples/step_13_fastapi/04_bearer_auth.py

Requires:
    pip install "aoa-action-machine[jwt]" aoa-fastapi-adapter
"""

from datetime import UTC, datetime, timedelta

import jwt
from fastapi.testclient import TestClient
from pydantic import Field

from aoa.action_machine.auth import ApplicationRole, GuestRole, NoAuthCoordinator
from aoa.action_machine.auth.jwt_auth import JwtAuthCoordinator
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
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.fastapi import FastApiAdapter

# --- Signing config (shared by LoginAction and JwtAuthCoordinator -- see the
# "same parameters on both sides" discussion: secret_key and algorithm MUST
# match between whoever signs and whoever verifies; TTL is signing-side only) ---
_SECRET_KEY = "demo-only-secret-do-not-use-in-production"
_ALGORITHM = "HS256"
_TOKEN_TTL = timedelta(minutes=30)


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
    access_token: str = Field(description="Signed JWT bearer token")
    token_type: str = Field(default="bearer", description="RFC 6750 token type")
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

    @summary_aspect("Sign a JWT carrying sub (user_id) and roles; return it as a bearer token.")
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


@meta(description="A protected route -- only reachable with a valid admin Bearer token.", domain=OrdersDomain)
@check_roles(AdminRole)
class ListOrdersAction(BaseAction[ParamsStub, OrderSummaryResult]):

    @summary_aspect("Return a fixed confirmation message.")
    async def build_summary(self, params, state, box, connections) -> OrderSummaryResult:
        _ = (params, state, box, connections)
        return OrderSummaryResult(message="orders: [] -- reached with a valid admin Bearer token")


def build_app():
    machine = ActionProductMachine()

    # The adapter-wide default: strict, verifies every Bearer token it sees.
    strict_default = JwtAuthCoordinator(
        secret_key=_SECRET_KEY,
        algorithm=_ALGORITHM,
        role_registry={"admin": AdminRole},
    )

    return (
        FastApiAdapter(machine=machine, auth_coordinator=strict_default, title="Bearer Auth Demo")
        # /auth/login has no token to present yet -- explicit per-route exception.
        .post(
            "/auth/login",
            LoginAction,
            tags=["auth"],
            auth_coordinator=NoAuthCoordinator(context=Context()),
            connections={"user_store": UserStoreResource(_USER_STORE)},
        )
        # /orders inherits the strict default -- every call must carry a valid token.
        .get("/orders", ListOrdersAction, tags=["orders"])
        .build()
    )


def main() -> None:
    client = TestClient(build_app(), raise_server_exceptions=False)

    # 1. No token at all -> the strict default denies -> 403.
    no_token = client.get("/orders")
    print(f"GET /orders (no token)           -> {no_token.status_code} {no_token.json()}")

    # 2. Log in -> a real signed JWT (the /auth/login exception let this through).
    login = client.post("/auth/login", json={"username": "alice", "password": "wonderland"})
    token = login.json()["access_token"]
    print(f"POST /auth/login                 -> {login.status_code} (token acquired)")

    # 3. Valid Bearer token -> JwtAuthCoordinator verifies it, maps roles=["admin"]
    #    to AdminRole, and @check_roles(AdminRole) lets the call through -> 200.
    ok = client.get("/orders", headers={"Authorization": f"Bearer {token}"})
    print(f"GET /orders (valid Bearer)       -> {ok.status_code} {ok.json()}")

    # 4. Tampered signature (flip the token's last character) -> 403.
    tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
    bad_signature = client.get("/orders", headers={"Authorization": f"Bearer {tampered}"})
    print(f"GET /orders (tampered signature) -> {bad_signature.status_code} {bad_signature.json()}")

    # 5. Expired token (exp in the past) -> 403, same as a missing token.
    expired_payload = {
        "sub": "alice",
        "roles": ["admin"],
        "iat": datetime.now(UTC) - timedelta(hours=1),
        "exp": datetime.now(UTC) - timedelta(minutes=1),
    }
    expired_token = jwt.encode(expired_payload, _SECRET_KEY, algorithm=_ALGORITHM)
    expired = client.get("/orders", headers={"Authorization": f"Bearer {expired_token}"})
    print(f"GET /orders (expired token)      -> {expired.status_code} {expired.json()}")


if __name__ == "__main__":
    main()
