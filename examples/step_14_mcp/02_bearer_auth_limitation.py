"""
02_bearer_auth_limitation.py — Bearer/JWT does NOT work with McpAdapter (yet).

Issuing a token (LoginAction) works fine as an MCP tool -- it is a plain
Action, transport-agnostic, exactly like over HTTP. What does NOT work is
verifying that token on a LATER call: McpAdapter always calls
auth_coordinator.process(None), so JwtAuthCoordinator's
BearerCredentialExtractor has nothing to read a Bearer header from -- it
raises immediately.

Why, precisely (not just "MCP can't"):
  - stdio transport (the common case -- Claude Desktop, most local MCP
    clients): there is no HTTP request at all -- fundamentally impossible,
    not an AOA gap.
  - HTTP-based MCP transports (SSE / Streamable HTTP): the mcp SDK itself
    ships Bearer-auth middleware (mcp.server.auth.middleware.bearer_auth)
    for exactly this scenario -- the PROTOCOL supports it. But that is a
    different integration seam (ASGI middleware wrapping the whole HTTP
    app) than AOA's AuthCoordinator.process(request_data), which
    McpAdapter never wires up regardless of transport.

Tracked as https://github.com/bystrovmaxim/aoa/issues/113. See also
docs/extensions/jwt_draft.md and 04_bearer_auth.py (the FastAPI adapter,
where this DOES work end to end).

Run from repository root:
    uv run python examples/step_14_mcp/02_bearer_auth_limitation.py

Requires:
    pip install "aoa-action-machine[jwt]" aoa-mcp-adapter
"""

import asyncio
from datetime import UTC, datetime, timedelta

import jwt
from pydantic import Field

from aoa.action_machine.auth import GuestRole, NoAuthCoordinator
from aoa.action_machine.auth.jwt_auth import JwtAuthCoordinator
from aoa.action_machine.context import Context
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.exceptions import AuthorizationError
from aoa.action_machine.intents.aspects import regular_aspect, summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.checkers import result_instance, result_string
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.mcp import McpAdapter

_SECRET_KEY = "demo-only-secret-do-not-use-in-production"
_ALGORITHM = "HS256"
_TOKEN_TTL = timedelta(minutes=30)


class AuthDomain(BaseDomain):
    name = "auth"
    description = "Login and token issuance"


# Fake user store: username -> (password, role names). See step_13_fastapi/03_login_action.py.
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


# ── Phase 1: login as an MCP tool -- this part WORKS, transport-agnostic ────
@meta(description="Authenticate a username/password pair and issue a JWT.", domain=AuthDomain)
@check_roles(GuestRole)
class LoginAction(BaseAction[LoginParams, LoginResult]):

    @result_string("user_id", required=True, not_empty=True)  # type: ignore[untyped-decorator]
    @result_instance("role_names", list, required=True)  # type: ignore[untyped-decorator]
    @regular_aspect("Verify username/password against the user store; resolve role names.")
    async def authenticate_user_aspect(self, params: LoginParams, state, box, connections) -> dict:
        _ = (state, box, connections)
        record = _USER_STORE.get(params.username)
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


def build_server():
    machine = ActionProductMachine()
    return (
        McpAdapter(
            machine=machine,
            auth_coordinator=NoAuthCoordinator(context=Context()),
            server_name="Bearer Limitation Demo",
        )
        .tool("auth.login", LoginAction)
        .build()
    )


async def main() -> None:
    server = build_server()

    # 1. Login over MCP -- works, exactly like over HTTP. LoginAction doesn't
    #    know or care what transport called it.
    result = await server.call_tool("auth.login", {"username": "alice", "password": "wonderland"})
    print(f"call_tool('auth.login', ...) -> isError={result.isError}")

    # 2. Now wire JwtAuthCoordinator the way 04_bearer_auth.py does for
    #    FastAPI, and reproduce exactly what McpAdapter calls on every single
    #    tool invocation: auth_coordinator.process(None).
    strict = JwtAuthCoordinator(secret_key=_SECRET_KEY, role_registry={})
    print("\nauth_coordinator.process(None) -- what McpAdapter actually calls on every tool call:")
    try:
        await strict.process(None)
    except TypeError as exc:
        print(f"  {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    asyncio.run(main())
