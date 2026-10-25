<!-- translated-from: jwt_draft.md @ 2026-07-11T14:10:43Z (filesystem mtime; draft is gitignored, no git history) · sha256:fbf9dce9a47c -->
<p align="center">
  <img src="../assets/aoa-logo.png" alt="AOA" width="200">
</p>

# Bearer / JWT — a ready-made authentication coordinator

<table width="100%"><tr>
  <td align="left"></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"></td>
</tr></table>

- [What it is](#what-it-is)
- [Installation](#installation)
- [Two phases: issuing and verifying](#two-phases-issuing-and-verifying)
- [Full cycle — FastAPI](#full-cycle--fastapi)
- [The session id](#the-session-id)
- [Read the session id in an aspect](#read-the-session-id-in-an-aspect)
- [Use the session id in an access rule](#use-the-session-id-in-an-access-rule)
- [Required claims: refusal or contract failure](#required-claims-refusal-or-contract-failure)
- [Migrating existing JWT code](#migrating-existing-jwt-code)
- [MCP — it doesn't work, and here's why](#mcp--it-doesnt-work-and-heres-why)
- [Transport: header or cookie](#transport-header-or-cookie)
- [External IdP: RS256 and JWKS](#external-idp-rs256-and-jwks)
- [Roles: mapping the claim to classes](#roles-mapping-the-claim-to-classes)
- [Variants](#variants)
- [API surface](#api-surface)

---

`JwtAuthCoordinator` is a ready-made [`AuthCoordinator`](../tutorials/step-12-authentication.md) that verifies `Authorization: Bearer <jwt>` on every request: signature, expiry, optionally `audience`/`issuer`, roles — and a mandatory session identifier — from the token's claims. The verification key is either a static secret the service signs its own tokens with (`secret_key`), or the JWKS of an external identity provider (`jwks_url` — Keycloak, Auth0, Google, an in-house token service; see [«External IdP: RS256 and JWKS»](#external-idp-rs256-and-jwks)). Either way, no session store is kept — the token carries everything needed, verification requires no trip to a database.

**Issuing the token (login) is out of scope.** `JwtAuthCoordinator` only **verifies** a Bearer token on an incoming request. How an application issues a token at login is an ordinary `LoginAction` that signs a JWT with PyJWT directly; no special class ships for this (see [below](#two-phases-issuing-and-verifying)).

## What it is

`aoa.action_machine.auth.jwt_auth` — five classes:

- **`BearerCredentialExtractor`** (`CredentialExtractor`) — pulls the token out of `Authorization: Bearer <jwt>`. An empty/malformed header → `{}` (no credentials); `request_data` with no `.headers` at all → `TypeError` (a wiring error, not "no credentials" — see the [MCP section](#mcp--it-doesnt-work-and-heres-why)).
- **`CookieCredentialExtractor`** (`CredentialExtractor`) — the same contract, but pulls the token out of a named cookie (`request_data.cookies`) instead of a header — see [«Transport: header or cookie»](#transport-header-or-cookie).
- **`JwtAuthenticator`** (`Authenticator`) — `jwt.decode(...)` with a fixed allowlist of algorithms (not whatever the token itself claims — otherwise algorithm confusion), checks the mandatory `exp`, optionally `audience`/`issuer`, maps the `roles` claim (a list of strings) to `BaseRole` classes via `role_registry`, and reads two required identifiers: the caller (`user_id_claim`, default `sub`) and the login session (`session_id_claim`, no default). The verification key is either a static `secret_key` or a JWKS endpoint `jwks_url` (exactly one of the two, else `ValueError` at construction) — see [«External IdP: RS256 and JWKS»](#external-idp-rs256-and-jwks). A token that fails verification → `None`; a verified token with a broken required identifier → `AuthenticationContractError` — see [«Required claims: refusal or contract failure»](#required-claims-refusal-or-contract-failure).
- **`HttpContextAssembler`** (`ContextAssembler`) — the default `RequestInfo` projection built from `request_data.url.path`/`.method`/`.client.host` (Starlette `Request`).
- **`JwtAuthCoordinator`** (`AuthCoordinator`) — a thin subclass that just assembles the three components above; no `process()` logic of its own. The extractor is swappable via `credential_extractor=` (`None` by default → `BearerCredentialExtractor()`), symmetric with the existing `context_assembler=`.

## Installation

```bash
pip install "aoa-action-machine[jwt]"
```

The extra pulls in `PyJWT[crypto]` — PyJWT itself is lightweight and pure-Python, `[crypto]` adds `cryptography` (needed to verify RS256/ES256 — without it, asymmetric algorithms fail at runtime, not at install time). `aoa.action_machine.auth` (the core namespace) never imports `jwt_auth` — without the extra, neither `PyJWT` nor `cryptography` ever loads into memory, not even transitively.

## Two phases: issuing and verifying

```
LoginAction (your code, GuestRole)         JwtAuthCoordinator (built in)
        │                                          │
   username/password                        Authorization: Bearer <jwt>
        │                                          │
   jwt.encode(...)                          jwt.decode(...) + role_registry
        │                                          │
        ▼                                          ▼
  access_token in Result                    Context(user=UserInfo(...))
```

**The secret and the algorithm must match on both sides** — this is a symmetric key (HS256): `JwtAuthCoordinator` verifies with the same `secret_key` that `LoginAction` used to sign. The lifetime (`TOKEN_TTL`) is a signing-side-only parameter: it's already baked into the token's `exp` claim, the verifying side never needs to know the TTL itself.

This shape has the service play both issuer and verifier. When the issuer is an external IdP (Keycloak, Auth0, Google) and there's no `LoginAction` in the service at all, the left half of the diagram doesn't exist: the service only verifies, and never holds the issuer's key material at all — see [«External IdP: RS256 and JWKS»](#external-idp-rs256-and-jwks).

## Full cycle — FastAPI

A working, run-verified example in two files:

**Issuing** — [`examples/step_13_fastapi/03_login_action.py`](../../examples/step_13_fastapi/03_login_action.py) ([▶ Try in Colab](#03_login_action.ipynb)). `LoginAction` — two aspects: check the username/password (on mismatch — `AuthorizationError`, the same message for a wrong password and for an unknown user — no username enumeration), sign the JWT (`sub`, `sid`, `roles`, `iat`, `exp`); every login gets a new `sid` — see [«The session id»](#the-session-id).

**Verifying** — [`examples/step_13_fastapi/04_bearer_auth.py`](../../examples/step_13_fastapi/04_bearer_auth.py) ([▶ Try in Colab](#04_bearer_auth.ipynb)). `JwtAuthCoordinator` is the adapter's strict default; `/auth/login` is an explicit [route-level override](../tutorials/step-12-authentication.md#route-level-override) (`NoAuthCoordinator`), because login has no token to present yet:

```python
strict_default = JwtAuthCoordinator(
    secret_key=_SECRET_KEY,
    algorithm=_ALGORITHM,
    role_registry={"admin": AdminRole},
    session_id_claim="sid",
)

FastApiAdapter(machine=machine, auth_coordinator=strict_default, title="Bearer Auth Demo") \
    .post("/auth/login", LoginAction, auth_coordinator=NoAuthCoordinator(context=Context())) \
    .get("/orders", ListOrdersAction) \
    .build()
```

A real run (`uv run python examples/step_13_fastapi/04_bearer_auth.py`):

```text
GET /orders (no token)           -> 403 {'detail': 'Authentication required'}
POST /auth/login                 -> 200 (token acquired)
GET /orders (valid Bearer)       -> 200 {'message': 'orders: [] -- reached with a valid admin Bearer token'}
GET /orders (tampered signature) -> 403 {'detail': 'Authentication required'}
GET /orders (expired token)      -> 403 {'detail': 'Authentication required'}
```

Five scenarios: no token (the default denied), login (the route-level override let it through), a valid Bearer token (the coordinator verified the signature, mapped `roles=["admin"]` → `AdminRole`, `@check_roles(AdminRole)` let it through), a tampered signature, an expired token — the last two give the same 403 as a missing token: no detail about the reason for the denial leaks to the caller.

## The session id

An authenticated JWT request identifies two things: the caller and the login session. `UserInfo.user_id` comes from the user-id claim (`sub` by default). `UserInfo.session_id` comes from the session claim. With both, two logins of one user stay two separate principals — in audit records and in any rule that reasons about a session. With `sub` alone they merge.

Issuers name the session claim differently, so its name is configuration: `session_id_claim`. The field it fills, `session_id`, is the same for every issuer. The argument is required on both `JwtAuthenticator` and `JwtAuthCoordinator`. It has no default, and no setting turns the check off.

From [`07_session_id.py`](../../examples/step_13_fastapi/07_session_id.py):

```python
auth = JwtAuthCoordinator(
    secret_key=_SECRET_KEY,
    algorithm=_ALGORITHM,
    role_registry={"viewer": ViewerRole},
    session_id_claim="sid",
)
```

A wrong declaration fails when the object is constructed, before any request arrives:

| Declaration | Error at construction |
|---|---|
| `session_id_claim` left out | `TypeError: JwtAuthCoordinator.__init__() missing 1 required keyword-only argument: 'session_id_claim'` |
| `session_id_claim=""` | `ValueError: session_id_claim must be a non-empty string; got ''.` |
| `session_id_claim=None`, or any non-string | `ValueError: session_id_claim must be a non-empty string; got None.` (the repr of the value) |

`JwtAuthenticator` raises the same errors with its own class name in the `TypeError`.

**One login, one session.** The issuer gives each new login a new identifier. When it refreshes a token inside the same login, the new token keeps the identifier. A session id is not a token id: `jti` names one token, the session id names the login behind it.

**AOA carries the value and nothing more.** It reads the claim from a verified token and puts it into the context unchanged. It does not generate identifiers, check that they are unique, store sessions, log out or revoke. If an issuer reuses one value for two logins, AOA cannot tell them apart.

**An identifier, not a secret.** The token's signature is the proof of identity. The session id proves nothing, and knowing it gives no access.

**Machine tokens need the claim too.** Every token the coordinator accepts must carry it, including server-to-server tokens whose issuer has no notion of a login. Such an issuer has to add the claim, for example one identifier per issued grant. Until it does, its tokens raise `AuthenticationContractError` (see [below](#required-claims-refusal-or-contract-failure)).

[`07_session_id.py`](../../examples/step_13_fastapi/07_session_id.py) · [notebook](../../examples/step_13_fastapi/07_session_id.ipynb) · [▶ Try in Colab](#07_session_id.ipynb) — the configuration errors above, then a service that issues its own tokens: two logins get two sessions, and a refresh keeps the session. A real run:

```text
no session_id_claim  -> TypeError: JwtAuthCoordinator.__init__() missing 1 required keyword-only argument: 'session_id_claim'
session_id_claim=''  -> ValueError: session_id_claim must be a non-empty string; got ''.
GET /me (laptop token)    -> {'user_id': 'alice', 'session_id': 'session-1'}
GET /me (phone token)     -> {'user_id': 'alice', 'session_id': 'session-2'}
refreshed token is new    -> True
GET /me (refreshed token) -> {'user_id': 'alice', 'session_id': 'session-1'}
```

## Read the session id in an aspect

The session id is an ordinary context field. An aspect declares it in `@context_requires(Ctx.User.session_id)` and reads it with `ctx.get(Ctx.User.session_id)` — the same way it reads `Ctx.User.user_id`. There is no need to decode the token again. A complete program:

```python
import asyncio
from datetime import UTC, datetime, timedelta

import jwt
from pydantic import Field

from aoa.action_machine.auth import ApplicationRole
from aoa.action_machine.auth.jwt_auth import JwtAuthenticator
from aoa.action_machine.context import Context, ContextView, Ctx
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.context_requires import context_requires
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseResult, ParamsStub
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.resources import Connections
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.action_machine.runtime.tools_box import ToolsBox

SECRET_KEY = "demo-only-secret-do-not-use-in-production"


class AuthDomain(BaseDomain):
    name = "auth"
    description = "Identity"


class ViewerRole(ApplicationRole):
    name = "viewer"
    description = "Read-only access."


class SessionResult(BaseResult):
    session_id: str = Field(description="Login session identifier")


@meta(description="Report the caller's login session.", domain=AuthDomain)
@check_roles(ViewerRole)
class SessionAction(BaseAction[ParamsStub, SessionResult]):

    @summary_aspect("Read the session id.")
    @context_requires(Ctx.User.session_id)
    async def session_summary(self, params: ParamsStub, state: BaseState, box: ToolsBox, connections: Connections, ctx: ContextView) -> SessionResult:
        return SessionResult(session_id=ctx.get(Ctx.User.session_id))


async def main() -> None:
    auth = JwtAuthenticator(secret_key=SECRET_KEY, role_registry={"viewer": ViewerRole}, session_id_claim="sid")
    claims = {"sub": "alice", "sid": "session-1", "roles": ["viewer"], "exp": datetime.now(UTC) + timedelta(minutes=5)}
    token = jwt.encode(claims, SECRET_KEY, algorithm="HS256")

    user = await auth.authenticate({"token": token})
    print(user)

    result = await ActionProductMachine().run(Context(user=user), SessionAction(), ParamsStub())
    print(result)


asyncio.run(main())
```

```text
user_id='alice' session_id='session-1' roles=(<class '__main__.ViewerRole'>,)
session_id='session-1'
```

Behind an adapter, `JwtAuthCoordinator` does the `authenticate` step and assembles the `Context`; the aspect is the same.

`UserInfo.session_id` is optional (`str | None`). After a successful JWT authentication it is always a non-blank string. Other sources leave it `None` unless they set it: an anonymous `UserInfo()`, `NoAuthCoordinator(context=Context())`, or your own `Authenticator`.

## Use the session id in an access rule

An `@access_decide` method reads the session id the same way and may base its verdict on it. AOA puts no special limits on such rules: the session id is typed context data like any other field.

Because AOA keeps no session store, ending a session is application logic. In [`08_session_access_rule.py`](../../examples/step_13_fastapi/08_session_access_rule.py), `LogoutAction` records the caller's session in an application registry, and the rule refuses a recorded session:

```python
@access_decide("Refuse a session the application has ended")
@context_requires(Ctx.User.session_id)
async def active_session_access_decide(self, params: ParamsStub, box: ToolsBox, connections: Connections, ctx: ContextView) -> Verdict:
    if await connections["sessions"].is_ended(ctx.get(Ctx.User.session_id)):
        return Refused("SESSION_ENDED")
    return Allowed()
```

The ended session's token is still signed and unexpired, so authentication accepts it. The refusal comes from the rule, and `FastApiAdapter` answers it with `403`. The same user's other session keeps working:

```text
GET /orders (laptop, active)  -> 200 {'orders': ['ord-001']}
POST /auth/logout (laptop)    -> 200 {'ended_session': 'session-1'}
GET /orders (laptop, ended)   -> 403 {'detail': 'Access denied by ACCESS_DECIDE: SESSION_ENDED'}
GET /orders (phone, active)   -> 200 {'orders': ['ord-001']}
```

[`08_session_access_rule.py`](../../examples/step_13_fastapi/08_session_access_rule.py) · [notebook](../../examples/step_13_fastapi/08_session_access_rule.ipynb) · [▶ Try in Colab](#08_session_access_rule.ipynb). How object rules work in general — [Roles and object rules](../how-to/roles-and-object-rules.md).

## Required claims: refusal or contract failure

`JwtAuthenticator.authenticate` answers "no" in two different ways.

**A token that fails verification is refused.** A bad signature, an expired lifetime, a wrong `audience` or `issuer`, a missing `exp`, a string that is not a JWT, a JWKS key that cannot be resolved (unreachable endpoint, unknown `kid`, malformed document) — all return `None`. Over FastAPI this is `403 {'detail': 'Authentication required'}`. The caller learns nothing about the reason.

**A verified token with a broken required identifier raises.** Both the user-id claim (`user_id_claim`, default `sub`) and the session claim must be non-blank strings. Anything else raises `AuthenticationContractError` during `authenticate()`, before the `Context` is assembled. No Action, aspect or access rule runs.

| Claim value in a verified token | `exc.reason` | Message |
|---|---|---|
| absent, or `null` | `missing` | `Required claim 'sid' must be a non-blank string: missing.` |
| `""` | `empty` | `Required claim 'sid' must be a non-blank string: empty.` |
| only whitespace (`" \t\n"`, a no-break space — anything `str.isspace()` accepts) | `whitespace-only` | `Required claim 'sid' must be a non-blank string: whitespace-only.` |
| a number, a boolean, a list, an object | `not a string` | `Required claim 'sid' must be a non-blank string: not a string.` |

The exception lives in `aoa.action_machine.exceptions`. `exc.claim` is the configured claim name (`'sid'`, `'sub'`, or your custom `user_id_claim`), and `exc.reason` is one of the four reasons above. Neither the message nor the attributes carry the claim's value or the token.

**Verification comes first.** A token that fails verification returns `None` even when its identifiers are also broken: an expired token with a numeric `sub`, or a foreign signature over an empty `sid`. Only a token the service would otherwise trust can raise the contract error.

**Every other string is accepted as written.** `" Session-A "` stays `" Session-A "`: no trimming, no case folding, no format check. The same holds for the user id.

**A numeric `sub` is refused, not converted.** PyJWT rejects a non-string `sub` while decoding, and AOA reports that as the contract error for `sub`. The issuer must emit a string:

```text
{"sub": 12345}    -> AuthenticationContractError: Required claim 'sub' must be a non-blank string: not a string.
{"sub": "12345"}  -> UserInfo(user_id='12345', ...)
```

**A custom user-id claim.** With `user_id_claim="uid"`, the error names `uid` when that claim is broken. A numeric registered `sub` in the same token is still refused by PyJWT, and that error names `sub`, not `uid`.

**Over HTTP a contract failure is a server error.** `FastApiAdapter` answers it with `500 {'detail': 'Internal server error'}`. The response does not carry the claim name or the reason, and the adapter does not log the exception. The failure points at the issuer's configuration, not at the caller.

**Other errors propagate too.** A programming error or a missing dependency inside token verification or JWKS resolution reaches the caller as its own exception. It does not turn into `None`.

[`09_required_claims.py`](../../examples/step_13_fastapi/09_required_claims.py) · [notebook](../../examples/step_13_fastapi/09_required_claims.ipynb) · [▶ Try in Colab](#09_required_claims.ipynb) — every case above with real tokens. A real run:

```text
-- 1. verification comes first
signed with another key        -> None
expired                        -> None
no exp claim                   -> None
not a JWT                      -> None
-- 2. the session claim
sid missing                    -> AuthenticationContractError: Required claim 'sid' must be a non-blank string: missing.
sid null                       -> AuthenticationContractError: Required claim 'sid' must be a non-blank string: missing.
sid empty                      -> AuthenticationContractError: Required claim 'sid' must be a non-blank string: empty.
sid whitespace-only            -> AuthenticationContractError: Required claim 'sid' must be a non-blank string: whitespace-only.
sid not a string               -> AuthenticationContractError: Required claim 'sid' must be a non-blank string: not a string.
sid ' Session-A '              -> ('alice', ' Session-A ')
-- 3. the user-id claim
sub 12345 (number)             -> AuthenticationContractError: Required claim 'sub' must be a non-blank string: not a string.
sub '12345' (string)           -> ('12345', 'session-1')
sub missing                    -> AuthenticationContractError: Required claim 'sub' must be a non-blank string: missing.
uid missing                    -> AuthenticationContractError: Required claim 'uid' must be a non-blank string: missing.
uid 'alice-01'                 -> ('alice-01', 'session-1')
uid ok, sub 12345 (number)     -> AuthenticationContractError: Required claim 'sub' must be a non-blank string: not a string.
-- 4. the same tokens over HTTP
GET /session (valid token)               -> 200 {'session_id': 'session-1'}
GET /session (expired token)             -> 403 {'detail': 'Authentication required'}
GET /session (verified token, sid empty) -> 500 {'detail': 'Internal server error'}
```

## Migrating existing JWT code

Code written for the previous version needs two changes: every constructor call names the session claim, and every issuer puts that claim into its tokens.

```python
# Before
JwtAuthCoordinator(secret_key=SECRET_KEY, role_registry={"admin": AdminRole})

# Now
JwtAuthCoordinator(secret_key=SECRET_KEY, role_registry={"admin": AdminRole}, session_id_claim="sid")
```

Some tokens get a different answer than before:

| Verified token | Before | Now |
|---|---|---|
| no session claim | accepted | `AuthenticationContractError` |
| `sub` missing or `""` | `None` (refusal, 403) | `AuthenticationContractError` (500 over FastAPI) |
| `{"sub": 12345}` | `None` (refusal, 403) | `AuthenticationContractError` for `sub` |
| `sub` of whitespace only | accepted as is | `AuthenticationContractError` |
| custom `user_id_claim` holding a number (`{"uid": 42}`) | accepted as `"42"` | `AuthenticationContractError` |

Code that treated "no user id" as an ordinary refusal now sees an exception instead. Fix the issuer rather than catching it: the token is valid, its content is not.

## MCP — it doesn't work, and here's why

**Short version: `JwtAuthCoordinator` will not work with `McpAdapter`.** Not "untested yet" — it genuinely crashes on the very first tool call:

```text
TypeError: BearerCredentialExtractor requires request_data exposing a `.headers` mapping
(e.g. a Starlette/FastAPI Request); got None. This coordinator cannot be used with an
adapter that never forwards request data — e.g. aoa-mcp-adapter always calls
process(None), regardless of transport.
```

There isn't one reason — there are three, and they're of very different scope:

1. **stdio transport** (the common case — Claude Desktop and most local MCP clients) — this is a raw JSON-RPC pipe over stdin/stdout. There is no HTTP request at all, so there's nowhere for an `Authorization` header to come from. This is a transport limitation, not an AOA or SDK gap — no framework can fix it.
2. **HTTP-based MCP transports (SSE / Streamable HTTP)** — here Bearer/JWT is natively supported **by the protocol itself**: the installed `mcp` SDK already ships `mcp.server.auth.middleware.bearer_auth.BearerAuthBackend` — a Starlette `AuthenticationBackend` that reads `Authorization: Bearer` off the raw HTTP connection and verifies it through a pluggable `TokenVerifier` (a conceptual counterpart to our own `Authenticator`). So the transport and the SDK are not the blocker.
3. **AOA's own `McpAdapter` implementation** — this is where the real, AOA-specific gap is: `_execute_tool_call` **always** calls `auth_coordinator.process(None)`, regardless of transport — even when the server runs on an HTTP-based transport where a real request with real headers exists. Wiring in `BearerAuthBackend` happens at the ASGI-middleware layer, wrapping the entire HTTP app, before JSON-RPC dispatch — not at the level of the `Tool.fn` handler that `_execute_tool_call` calls. Threading the real request through `AuthCoordinator.process(request_data)` for HTTP-based transports is a separate adapter change, outside the scope of the JWT coordinator itself.

A full demonstration (both phases, including the explicit failure) — [`examples/step_14_mcp/02_bearer_auth_limitation.py`](../../examples/step_14_mcp/02_bearer_auth_limitation.py) ([▶ Try in Colab](#02_bearer_auth_limitation.ipynb)): `LoginAction`, exposed as an MCP tool, works exactly as usual (an Action doesn't know and shouldn't need to know the transport), while trying to use `JwtAuthCoordinator` as the adapter's `auth_coordinator` fails explicitly.

Tracked in [issue #113](https://github.com/bystrovmaxim/aoa/issues/113). Until it's resolved, the only working `auth_coordinator` for `McpAdapter` is `NoAuthCoordinator`, regardless of transport.

## Transport: header or cookie

A Bearer token lives in the `Authorization` header, which **the client sets itself** — usually by copying the token from the login response into JS code, a mobile app, or a CLI. That fits naturally where the client controls the request programmatically: API-to-API, CLI, mobile apps.

For browser-based SSO across subdomains (`app.example.com`, `admin.example.com`, ...) that model doesn't just get awkward, it stops working entirely: a central login service sets an `httpOnly` cookie on the parent domain (`Set-Cookie: session=...; Domain=.example.com; HttpOnly`). The browser attaches that cookie automatically to every request to every subdomain — but `HttpOnly` makes it invisible to JavaScript, so the frontend has no way to copy the token into an `Authorization` header. The token only ever arrives in the `Cookie:` header.

`CookieCredentialExtractor(cookie_name=...)` reads it from there — the contract is identical to `BearerCredentialExtractor`'s: an empty/missing cookie → `{}` (no credentials), `request_data` with no `.cookies` at all → `TypeError` (a wiring error — the same `McpAdapter` case as above).

It plugs straight into `JwtAuthCoordinator` — the `credential_extractor` parameter swaps `BearerCredentialExtractor` for any other `CredentialExtractor`; the rest of the pipeline (signature, `exp`, `role_registry`) is unchanged:

```python
auth = JwtAuthCoordinator(
    secret_key=...,
    role_registry={"admin": AdminRole},
    session_id_claim="sid",
    credential_extractor=CookieCredentialExtractor(cookie_name="session"),
)
```

**`SameSite` and subdomains.** `Domain=.example.com` makes the cookie visible on every subdomain of one eTLD+1 (`app.example.com`, `admin.example.com`, ...) — from `SameSite=Lax`'s point of view (the modern browser default for cookies), those all count as "the same site", so the cookie flows freely between them. A third-party domain (`evil.com`) still never receives it in a cross-site request — `SameSite`'s baseline CSRF protection holds regardless of how many subdomains the cookie is visible to.

**Which to choose:**

- **Header (`BearerCredentialExtractor`)** — the client controls the request programmatically and can explicitly attach the token: API-to-API, CLI, mobile apps, server-to-server integrations.
- **Cookie (`CookieCredentialExtractor`)** — browser-based SSO across subdomains via an `httpOnly` session: JavaScript cannot read the token by design, so Bearer isn't merely inconvenient here — it's architecturally impossible.

A working example — [`examples/step_13_fastapi/05_cookie_auth.py`](../../examples/step_13_fastapi/05_cookie_auth.py) ([▶ Try in Colab](#05_cookie_auth.ipynb)): `LoginAction` sets `Set-Cookie: session=...; HttpOnly`, the protected route is reached with no `Authorization` header at all — only through the cookie the client stored, and the coordinator is a plain `JwtAuthCoordinator` with `credential_extractor=CookieCredentialExtractor(...)`.

## External IdP: RS256 and JWKS

`secret_key` is a shared static key: HS256 within one service, or a mounted public key for RS256/ES256. At scale this shape has two operational downsides: the verification key has to be copied into every consumer (a file per container, an ops step per service), and rotation is all-or-nothing — consumers hold exactly one key, so rotating the issuer's key instantly invalidates every outstanding token (mass logout).

The industry answer is **JWKS** (RFC 7517): the issuer publishes its public keys at a URL like `https://issuer/.well-known/jwks.json`, every token carries a `kid` header, and verifiers fetch and cache the key set and pick the right one by `kid`. Rotation becomes seamless: publish old+new, sign with the new key, drop the old one once outstanding tokens expire. The consumer holds no key material at all — only a URL. PyJWT supports this natively via `jwt.PyJWKClient`, no new dependency required.

```python
auth = JwtAuthCoordinator(
    jwks_url="https://sso.example.com/.well-known/jwks.json",
    algorithm="RS256",
    issuer="https://sso.example.com",
    audience="my-platform",
    role_registry={"admin": AdminRole},
    session_id_claim="sid",
)
```

`jwks_url` and `secret_key` are mutually exclusive — exactly one of the two is required, else `ValueError` at construction (fail-fast, same as every other declaration-time check). The allowlist passed to `jwt.decode` is still exactly one algorithm — whatever `algorithm=` says, never whatever the token itself claims (algorithm-confusion protection is unchanged).

**`issuer` is now validated too.** Previously `iss` was ignored outright; `issuer=...` turns on validation (a mismatch rejects the token), `issuer=None` (the default) — same as before, `iss` is not checked. Works identically for a static key and for JWKS.

**A key that cannot be resolved is a refusal.** An unreachable JWKS endpoint, an unknown `kid`, a token with no `kid` at all, a malformed JWKS document — all of it degrades to `None`, the same as any other verification failure. Unexpected errors in this step propagate. A verified token with a broken user-id or session claim raises `AuthenticationContractError` — see [«Required claims: refusal or contract failure»](#required-claims-refusal-or-contract-failure).

**Packaging.** RS256/ES256 signature verification needs `cryptography` — the `aoa-action-machine[jwt]` extra now pulls in `PyJWT[crypto]` instead of plain `PyJWT`.

**Static key or JWKS:**

| | Static key (`secret_key`) | JWKS (`jwks_url`) |
|---|---|---|
| Topology | One service signs and verifies itself | One central IdP, many verifying services |
| Key on the consumer | Yes (an HS256 secret, or a mounted public key) | No — a URL only |
| Rotation | All-or-nothing, logs every token out at once | Seamless — publish old+new, then drop the old one |
| Typical IdP | Your own | Keycloak, Auth0, Google, an in-house token service |

A working example — [`examples/step_13_fastapi/06_jwks_auth.py`](../../examples/step_13_fastapi/06_jwks_auth.py) ([▶ Try in Colab](#06_jwks_auth.ipynb)): generates an RSA keypair and a local JWKS document right in the example, `LoginAction` signs RS256 with a `kid` header, the protected route verifies through `jwks_url` with `issuer=` set, plus a negative case — a token from a "foreign" issuer gets rejected.

## Roles: mapping the claim to classes

A JWT carries roles as strings (`"roles": ["admin", "viewer"]`), while `UserInfo.roles` is a tuple of `BaseRole` classes. `role_registry` is the explicit dict the developer supplies:

```python
JwtAuthCoordinator(secret_key=..., role_registry={"admin": AdminRole, "viewer": ViewerRole}, session_id_claim="sid")
```

Unmapped names in the claim are silently dropped rather than rejecting the token outright — in a multi-service system a token may legitimately carry roles that mean nothing to this particular service. For the same reason, a malformed claim shape (not a list) yields an empty roles tuple rather than an authentication failure — identity is still established, just with zero roles (`@check_roles` will only let `GuestRole` operations through).

## Variants

- **Static key vs. RS256/JWKS.** See [«External IdP: RS256 and JWKS»](#external-idp-rs256-and-jwks) — `secret_key`/`jwks_url` are mutually exclusive, `issuer=` optionally validates `iss`.
- **One long-lived token (as in the demo) vs. an access+refresh pair.** The demo example uses a single 30-minute token. There is no built-in support for refresh tokens — if needed, issuing them (another `LoginAction`-like Action) and storing them stays application code, just like login itself. A refreshed token keeps the session id of the login it continues; [`07_session_id.py`](../../examples/step_13_fastapi/07_session_id.py) shows a refresh Action that reads it from the context.

## API surface

`BearerCredentialExtractor()` · `CookieCredentialExtractor(cookie_name)` · `JwtAuthenticator(secret_key=None, jwks_url=None, algorithm="HS256", audience=None, issuer=None, role_registry, user_id_claim="sub", roles_claim="roles", session_id_claim)` · `HttpContextAssembler()` · `JwtAuthCoordinator(secret_key=None, jwks_url=None, algorithm="HS256", audience=None, issuer=None, role_registry, user_id_claim="sub", roles_claim="roles", session_id_claim, credential_extractor=None, context_assembler=None)`. Every argument is keyword-only; `role_registry` and `session_id_claim` have no default.

In the context: `UserInfo.session_id: str | None`, read as `Ctx.User.session_id` (`"user.session_id"`). The contract error: `aoa.action_machine.exceptions.AuthenticationContractError` with `.claim` and `.reason`.

How authentication is structured overall — the chapter [Authentication](../tutorials/step-12-authentication.md); your own sign-in mechanism (Basic, API key, OAuth2, anything else) — [«Your own authentication coordinator»](../how-to/authoring-auth-coordinator.md).

---

<table width="100%"><tr>
  <td align="left"></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"></td>
</tr></table>
