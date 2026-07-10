"""
03_login_action.py — LoginAction: verify credentials, sign a JWT bearer token.

This is the FIRST half of JWT authentication — issuing a token. It is a plain
AOA Action, open to guests (`@check_roles(GuestRole)`), that signs a JWT with
PyJWT directly. No AOA-specific coordinator is involved in signing: that
machinery (BearerCredentialExtractor / JwtAuthenticator / JwtAuthCoordinator)
only comes in on the OTHER half — verifying a token on every later request.

Run from repository root:
    uv run python examples/step_13_fastapi/03_login_action.py

Requires:
    pip install "aoa-action-machine" aoa-fastapi-adapter pyjwt
"""

from datetime import UTC, datetime, timedelta

import jwt
from fastapi.testclient import TestClient
from pydantic import Field

from aoa.action_machine.auth import GuestRole, NoAuthCoordinator
from aoa.action_machine.context import Context
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.exceptions import AuthorizationError
from aoa.action_machine.intents.aspects import regular_aspect, summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.checkers import result_instance, result_string
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.fastapi import FastApiAdapter

# --- Signing config -----------------------------------------------------------
# In production this comes from a secret manager / env var, never a source constant.
_SECRET_KEY = "demo-only-secret-do-not-use-in-production"
_ALGORITHM = "HS256"
_TOKEN_TTL = timedelta(minutes=30)


class AuthDomain(BaseDomain):
    name = "auth"
    description = "Login and token issuance"


# Fake user store: username -> (password, role names).
# A real store hashes passwords (bcrypt/argon2) and never keeps or compares plaintext.
_USER_STORE: dict[str, tuple[str, list[str]]] = {
    "alice": ("wonderland", ["admin"]),
    "bob": ("builder", ["viewer"]),
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
class LoginAction(BaseAction[LoginParams, LoginResult]):
    """
    AI-CORE-BEGIN
    ROLE: Two-aspect pipeline -- verify credentials against the user store, then sign a JWT carrying user_id + roles.
    CONTRACT: Wrong username or wrong password both raise the same AuthorizationError message -- never reveal which one was wrong (no username enumeration).
    INVARIANTS: Password comparison here is a placeholder (plaintext) -- replace with a real hash check (bcrypt/argon2) before production use.
    AI-CORE-END
    """

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


def build_app():
    machine = ActionProductMachine()
    return (
        FastApiAdapter(machine=machine, auth_coordinator=NoAuthCoordinator(context=Context()), title="Login Demo")
        .post("/auth/login", LoginAction, tags=["auth"])
        .build()
    )


def main() -> None:
    client = TestClient(build_app(), raise_server_exceptions=False)

    # 1. Correct credentials -> a real signed JWT.
    ok = client.post("/auth/login", json={"username": "alice", "password": "wonderland"})
    print(f"POST /auth/login (alice, correct pw) -> {ok.status_code} {ok.json()}")

    token = ok.json()["access_token"]

    # 2. Decode WITHOUT verifying the signature -- purely to show what's inside.
    #    A real Bearer coordinator verifies the signature; see the next example.
    payload = jwt.decode(token, options={"verify_signature": False})
    print(f"Decoded payload (unverified, for illustration only) -> {payload}")

    # 3. Wrong password -> AuthorizationError -> HTTP 403.
    bad_password = client.post("/auth/login", json={"username": "alice", "password": "wrong"})
    print(f"POST /auth/login (alice, wrong pw)   -> {bad_password.status_code} {bad_password.json()}")

    # 4. Unknown username -> same 403, same message (no enumeration).
    unknown_user = client.post("/auth/login", json={"username": "carol", "password": "anything"})
    print(f"POST /auth/login (unknown user)      -> {unknown_user.status_code} {unknown_user.json()}")


if __name__ == "__main__":
    main()
