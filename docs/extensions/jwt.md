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
- [MCP — it doesn't work, and here's why](#mcp--it-doesnt-work-and-heres-why)
- [Transport: header or cookie](#transport-header-or-cookie)
- [External IdP: RS256 and JWKS](#external-idp-rs256-and-jwks)
- [Roles: mapping the claim to classes](#roles-mapping-the-claim-to-classes)
- [Variants](#variants)
- [API surface](#api-surface)

---

`JwtAuthCoordinator` is a ready-made [`AuthCoordinator`](../tutorials/step-12-authentication.md) that verifies `Authorization: Bearer <jwt>` on every request: signature, expiry, optionally `audience`/`issuer`, roles — from the token's claims. The verification key is either a static secret the service signs its own tokens with (`secret_key`), or the JWKS of an external identity provider (`jwks_url` — Keycloak, Auth0, Google, an in-house token service; see [«External IdP: RS256 and JWKS»](#external-idp-rs256-and-jwks)). Either way, no sessions need to be kept — the token carries everything needed, verification requires no trip to a database.

**Issuing the token (login) is out of scope.** `JwtAuthCoordinator` only **verifies** a Bearer token on an incoming request. How an application issues a token at login is an ordinary `LoginAction` that signs a JWT with PyJWT directly; no special class ships for this (see [below](#two-phases-issuing-and-verifying)).

## What it is

`aoa.action_machine.auth.jwt_auth` — five classes:

- **`BearerCredentialExtractor`** (`CredentialExtractor`) — pulls the token out of `Authorization: Bearer <jwt>`. An empty/malformed header → `{}` (no credentials); `request_data` with no `.headers` at all → `TypeError` (a wiring error, not "no credentials" — see the [MCP section](#mcp--it-doesnt-work-and-heres-why)).
- **`CookieCredentialExtractor`** (`CredentialExtractor`) — the same contract, but pulls the token out of a named cookie (`request_data.cookies`) instead of a header — see [«Transport: header or cookie»](#transport-header-or-cookie).
- **`JwtAuthenticator`** (`Authenticator`) — `jwt.decode(...)` with a fixed allowlist of algorithms (not whatever the token itself claims — otherwise algorithm confusion), checks the mandatory `exp`, optionally `audience`/`issuer`, maps the `roles` claim (a list of strings) to `BaseRole` classes via `role_registry`. The verification key is either a static `secret_key` or a JWKS endpoint `jwks_url` (exactly one of the two, else `ValueError` at construction) — see [«External IdP: RS256 and JWKS»](#external-idp-rs256-and-jwks). Any verification failure → `None` (the `Authenticator` contract: invalid → `None`, not an exception).
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

**Issuing** — [`examples/step_13_fastapi/03_login_action.py`](../../examples/step_13_fastapi/03_login_action.py) ([▶ Try in Colab](#03_login_action.ipynb)). `LoginAction` — two aspects: check the username/password (on mismatch — `AuthorizationError`, the same message for a wrong password and for an unknown user — no username enumeration), sign the JWT (`sub`, `roles`, `iat`, `exp`).

**Verifying** — [`examples/step_13_fastapi/04_bearer_auth.py`](../../examples/step_13_fastapi/04_bearer_auth.py) ([▶ Try in Colab](#04_bearer_auth.ipynb)). `JwtAuthCoordinator` is the adapter's strict default; `/auth/login` is an explicit [route-level override](../tutorials/step-12-authentication.md#route-level-override) (`NoAuthCoordinator`), because login has no token to present yet:

```python
strict_default = JwtAuthCoordinator(
    secret_key=_SECRET_KEY,
    algorithm=_ALGORITHM,
    role_registry={"admin": AdminRole},
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
)
```

`jwks_url` and `secret_key` are mutually exclusive — exactly one of the two is required, else `ValueError` at construction (fail-fast, same as every other declaration-time check). The allowlist passed to `jwt.decode` is still exactly one algorithm — whatever `algorithm=` says, never whatever the token itself claims (algorithm-confusion protection is unchanged).

**`issuer` is now validated too.** Previously `iss` was ignored outright; `issuer=...` turns on validation (a mismatch rejects the token), `issuer=None` (the default) — same as before, `iss` is not checked. Works identically for a static key and for JWKS.

**Failure is always `None`, never an exception.** An unreachable JWKS endpoint, an unknown `kid`, a token with no `kid` at all, a malformed JWKS document — all of it degrades to `None` (same as any other verification failure), never an unhandled exception somewhere mid-pipeline.

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
JwtAuthCoordinator(secret_key=..., role_registry={"admin": AdminRole, "viewer": ViewerRole})
```

Unmapped names in the claim are silently dropped rather than rejecting the token outright — in a multi-service system a token may legitimately carry roles that mean nothing to this particular service. For the same reason, a malformed claim shape (not a list) yields an empty roles tuple rather than an authentication failure — identity is still established, just with zero roles (`@check_roles` will only let `GuestRole` operations through).

## Variants

- **Static key vs. RS256/JWKS.** See [«External IdP: RS256 and JWKS»](#external-idp-rs256-and-jwks) — `secret_key`/`jwks_url` are mutually exclusive, `issuer=` optionally validates `iss`.
- **One long-lived token (as in the demo) vs. an access+refresh pair.** The demo example uses a single 30-minute token. There is no built-in support for refresh tokens — if needed, issuing them (another `LoginAction`-like Action) and storing them stays application code, just like login itself.

## API surface

`BearerCredentialExtractor()` · `CookieCredentialExtractor(cookie_name)` · `JwtAuthenticator(secret_key=None, jwks_url=None, algorithm="HS256", audience=None, issuer=None, role_registry, user_id_claim="sub", roles_claim="roles")` · `HttpContextAssembler()` · `JwtAuthCoordinator(secret_key=None, jwks_url=None, algorithm="HS256", audience=None, issuer=None, role_registry, user_id_claim="sub", roles_claim="roles", credential_extractor=None, context_assembler=None)`.

How authentication is structured overall — the chapter [Authentication](../tutorials/step-12-authentication.md); your own sign-in mechanism (Basic, API key, OAuth2, anything else) — [«Your own authentication coordinator»](../how-to/authoring-auth-coordinator.md).

---

<table width="100%"><tr>
  <td align="left"></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"></td>
</tr></table>
