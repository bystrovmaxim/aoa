"""
06_jwks_auth.py — JWKS: verify tokens from an external identity provider.

The other verification-key source (see 04_bearer_auth.py for the static-secret
path). Here nothing in this service signs tokens: a separate identity provider
holds the RSA private key and publishes only the public half at
`.well-known/jwks.json`; this service verifies purely from that URL and the
token's `kid` header (RFC 7517). To keep the example self-contained and
offline, `LoginAction` here plays the role of that external IdP -- in a real
deployment it would not exist in this service at all, see
docs/extensions/jwt_draft.md#внешний-idp-rs256-и-jwks.

What this demonstrates, beyond 04_bearer_auth.py:
  - An RSA keypair generated fresh on each run, and a local, loopback-only
    HTTP server (stdlib http.server, no new dependency) serving the public
    JWK at a real jwks_url -- JwtAuthenticator fetches it exactly like it
    would fetch a real IdP's endpoint, no key material mocked or bypassed.
  - JwtAuthCoordinator(jwks_url=..., issuer=...) instead of secret_key=.
  - issuer= rejects a token that resolves and verifies its signature
    correctly (same key, same kid) but claims a different `iss` -- a
    "foreign issuer" attack this example crafts by hand, without a second
    keypair or JWKS server, to isolate exactly what issuer validation buys.

Run from repository root:
    uv run python examples/step_13_fastapi/06_jwks_auth.py

Requires:
    pip install "aoa-action-machine[jwt]" aoa-fastapi-adapter
"""

import json
import threading
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from jwt.algorithms import RSAAlgorithm
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

_ALGORITHM = "RS256"
_ISSUER = "https://sso.example.com"
_KID = "demo-key-1"
_TOKEN_TTL = timedelta(minutes=30)

# A fresh RSA keypair for this run only -- never written to disk, never reused.
_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_PRIVATE_KEY_PEM = _private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
).decode()
_public_jwk = RSAAlgorithm.to_jwk(_private_key.public_key(), as_dict=True)
_public_jwk.update(kid=_KID, alg=_ALGORITHM, use="sig")
_JWKS_DOCUMENT = {"keys": [_public_jwk]}


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


class _JwksRequestHandler(BaseHTTPRequestHandler):
    """Serves a fixed JWKS document at every path -- stands in for a real IdP's endpoint."""

    def do_GET(self) -> None:
        body = json.dumps(_JWKS_DOCUMENT).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        pass  # silence default per-request logging to stderr


def _start_jwks_server() -> str:
    """Start a loopback-only JWKS server on an OS-assigned free port; return its URL."""
    server = HTTPServer(("127.0.0.1", 0), _JwksRequestHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    port = server.server_address[1]
    return f"http://127.0.0.1:{port}/.well-known/jwks.json"


class LoginParams(BaseParams):
    username: str = Field(description="Account username")
    password: str = Field(description="Account password")


class LoginResult(BaseResult):
    access_token: str = Field(description="Signed RS256 JWT, carrying this IdP's kid and iss")
    expires_in: int = Field(description="Token lifetime in seconds")


@meta(description="Authenticate a username/password pair and issue an RS256 JWT.", domain=AuthDomain)
@check_roles(GuestRole)
@connection(UserStoreResource, key="user_store")
class LoginAction(BaseAction[LoginParams, LoginResult]):
    """
    AI-CORE-BEGIN
    ROLE: Stand-in for an external IdP's token endpoint -- verify credentials, sign an RS256 JWT with this example's kid.
    CONTRACT: Wrong username or wrong password both raise the same AuthorizationError message -- no username enumeration. In a real deployment this class lives in the IdP, not in this service.
    AI-CORE-END
    """

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

    @summary_aspect("Sign an RS256 JWT carrying sub (user_id), roles, and iss -- with this IdP's kid header.")
    async def issue_token_summary(self, params: LoginParams, state, box, connections) -> LoginResult:
        _ = (params, box, connections)
        now = datetime.now(UTC)
        payload = {
            "sub": state["user_id"],
            "roles": state["role_names"],
            "iss": _ISSUER,
            "iat": now,
            "exp": now + _TOKEN_TTL,
        }
        token = jwt.encode(payload, _PRIVATE_KEY_PEM, algorithm=_ALGORITHM, headers={"kid": _KID})
        return LoginResult(access_token=token, expires_in=int(_TOKEN_TTL.total_seconds()))


class OrderSummaryResult(BaseResult):
    message: str = Field(description="Confirmation the caller reached a protected route")


@meta(description="A protected route -- only reachable with a valid admin token from the trusted issuer.", domain=OrdersDomain)
@check_roles(AdminRole)
class ListOrdersAction(BaseAction[ParamsStub, OrderSummaryResult]):

    @summary_aspect("Return a fixed confirmation message.")
    async def build_summary(self, params, state, box, connections) -> OrderSummaryResult:
        _ = (params, state, box, connections)
        return OrderSummaryResult(message="orders: [] -- reached with a valid admin token from the trusted JWKS issuer")


def build_app():
    machine = ActionProductMachine()
    jwks_url = _start_jwks_server()

    # jwks_url= instead of secret_key=: no key material on this service at all,
    # only a URL. issuer= makes iss mandatory -- a token that resolves and
    # verifies fine but claims a different issuer is still rejected.
    jwks_auth = JwtAuthCoordinator(
        jwks_url=jwks_url,
        algorithm=_ALGORITHM,
        issuer=_ISSUER,
        role_registry={"admin": AdminRole},
    )

    return (
        FastApiAdapter(machine=machine, auth_coordinator=jwks_auth, title="JWKS Auth Demo")
        .post(
            "/auth/login",
            LoginAction,
            tags=["auth"],
            auth_coordinator=NoAuthCoordinator(context=Context()),
            connections={"user_store": UserStoreResource(_USER_STORE)},
        )
        .get("/orders", ListOrdersAction, tags=["orders"])
        .build()
    )


def main() -> None:
    client = TestClient(build_app(), raise_server_exceptions=False)

    # 1. No token at all -> denied -> 403.
    no_token = client.get("/orders")
    print(f"GET /orders (no token)               -> {no_token.status_code} {no_token.json()}")

    # 2. Log in -> a real RS256 token, signed by the private key, verifiable only
    #    through the JWKS URL this service was configured with.
    login = client.post("/auth/login", json={"username": "alice", "password": "wonderland"})
    token = login.json()["access_token"]
    print(f"POST /auth/login                     -> {login.status_code} (RS256 token acquired)")

    # 3. Valid token -> JWKS resolves the kid, signature verifies, iss matches -> 200.
    ok = client.get("/orders", headers={"Authorization": f"Bearer {token}"})
    print(f"GET /orders (valid JWKS token)       -> {ok.status_code} {ok.json()}")

    # 4. Same key, same kid, signature verifies fine -- but a DIFFERENT iss.
    #    issuer= on the coordinator catches this even though nothing about the
    #    signature or the JWKS lookup is wrong.
    now = datetime.now(UTC)
    foreign_payload = {
        "sub": "alice",
        "roles": ["admin"],
        "iss": "https://a-different-issuer.example.com",
        "iat": now,
        "exp": now + _TOKEN_TTL,
    }
    foreign_token = jwt.encode(foreign_payload, _PRIVATE_KEY_PEM, algorithm=_ALGORITHM, headers={"kid": _KID})
    foreign = client.get("/orders", headers={"Authorization": f"Bearer {foreign_token}"})
    print(f"GET /orders (foreign issuer)         -> {foreign.status_code} {foreign.json()}")


if __name__ == "__main__":
    main()
