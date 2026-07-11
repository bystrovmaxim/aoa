<!-- translated-from: authoring-auth-coordinator_draft.md @ 2026-07-11T14:58:38Z (filesystem mtime; draft is gitignored, no git history) · sha256:be6efa8fed5f -->
<p align="center">
  <img src="../assets/aoa-logo.png" alt="AOA" width="200">
</p>

# Your own authentication coordinator

<table width="100%"><tr>
  <td align="left"></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"></td>
</tr></table>

- [When this is needed](#when-this-is-needed)
- [The contract: one method](#the-contract-one-method)
- [Path 1. Three parts on top of the ready AuthCoordinator](#path-1-three-parts-on-top-of-the-ready-authcoordinator)
- [Path 2. A fully custom process](#path-2-a-fully-custom-process)
- [What is important to know](#what-is-important-to-know)
- [Verification](#verification)

---

## When this is needed

A coordinator builds [`Context`](../tutorials/step-07-context.md) from a raw request **before** the machine runs: it extracts credentials (a JWT, an OAuth2 token, an API key, a session), verifies them, establishes the identity and roles. This is [Step 12 — Authentication](../tutorials/step-12-authentication.md) as a concept; here is how to write your own for a specific entry mechanism.

The full example: [02_custom_auth_coordinator.py](../../examples/how_to/02_custom_auth_coordinator.py).

## The contract: one method

A coordinator is an object with one async method:

```python
async def process(self, request_data) -> Context | None
```

`Context` — success (identity + request metadata). `None` — a hard reject at the boundary: the shipped adapters raise `AuthorizationError` (HTTP 403 / MCP `PERMISSION_DENIED`), and the request never reaches [`@check_roles`](../tutorials/step-03-authorization-and-roles.md) at all — that is not the same thing as anonymous access, which a coordinator declares explicitly rather than gets as a side effect of `None`. Authentication **produces** the identity, authorization **checks** the one already produced. For an open API there is `NoAuthCoordinator(context=Context())`: it does not participate in verification at all and always returns the same declared `Context` (usually anonymous — `user_id=None`, `roles=()`), leaving what an anonymous caller may do to `@check_roles`.

## Path 1. Three parts on top of the ready AuthCoordinator

The recommended path: do not write `process` by hand, but implement three small components — `AuthCoordinator` will assemble the pipeline `extract → authenticate → assemble → Context` from them.

**Step 1. The extractor** — pulls credentials out of the request. An empty dict = "no data" (the pipeline returns `None`):

```python
from aoa.action_machine.auth import CredentialExtractor

class ApiKeyExtractor(CredentialExtractor):
    async def extract(self, request_data) -> dict:
        key = request_data.headers.get("x-api-key")
        return {"api_key": key} if key else {}
```

**Step 2. The authenticator** — verifies the data and returns a `UserInfo` (with roles) or `None`. Invalid data is `None`, **not an exception**:

```python
from aoa.action_machine.auth import Authenticator
from aoa.action_machine.context import UserInfo

class ApiKeyAuthenticator(Authenticator):
    async def authenticate(self, credentials) -> UserInfo | None:
        record = _KEYS.get(credentials.get("api_key"))
        if record is None:
            return None
        user_id, roles = record
        return UserInfo(user_id=user_id, roles=roles)   # roles — a tuple of role classes
```

The roles in `UserInfo.roles` are **classes** (`BaseRole` subclasses, the name ends with `Role`), the same ones `@check_roles` later checks. This is [Step 3 — Roles](../tutorials/step-03-authorization-and-roles.md).

**Step 3. The assembler** — projects request metadata into kwargs for `RequestInfo` (trace, path, protocol, IP — for logs and tracing):

```python
from aoa.action_machine.auth import ContextAssembler

class HttpContextAssembler(ContextAssembler):
    async def assemble(self, request_data) -> dict:
        return {"request_path": request_data.path,
                "trace_id": request_data.headers.get("x-trace-id"),
                "protocol": "http"}
```

**Assembly** — pass the three parts into `AuthCoordinator`:

```python
from aoa.action_machine.auth import AuthCoordinator

coordinator = AuthCoordinator(ApiKeyExtractor(), ApiKeyAuthenticator(), HttpContextAssembler())
```

Inside, `process` does exactly this: `extract()` → if empty, `None`; `authenticate()` → if `None`, `None`; otherwise `assemble()` → `RequestInfo(**metadata)` → `Context(user=..., request=...)`.

## Path 2. A fully custom process

If the entry mechanism is more convenient to describe with one call (an external SSO, a ready identity-provider client), implement `process` directly — nothing to subclass, the adapter only needs the duck-typed contract:

```python
class SsoCoordinator:
    async def process(self, request_data) -> Context | None:
        token = request_data.headers.get("authorization")
        principal = await my_sso.verify(token)      # your external call
        if principal is None:
            return None
        return Context(user=UserInfo(user_id=principal.id, roles=principal.roles))
```

`NoAuthCoordinator` is built this way too — its constructor takes a ready-made `Context` (`NoAuthCoordinator(context=...)`), and `process` simply returns it on every call: the same object, not a new one.

## What is important to know

- **`None` is already a reject at the boundary.** The adapter raises `AuthorizationError("Authentication required")` (HTTP 403 / MCP `PERMISSION_DENIED`) — the request never reaches the machine or `@check_roles`. Need a more precise reason for the reject (an expired token, distinguished from a missing one, say) — **raise `AuthorizationError` with the message you want directly from `process`**, instead of relying on the generic default message.
- **Invalid data is `None`, not an exception** (the `Authenticator` contract): "wrong key" is a regular path, not a failure.
- **Where it is wired:** the coordinator is passed to the constructor of any adapter — `FastApiAdapter(machine, auth_coordinator=...)`, `McpAdapter(...)`, [your own adapter](authoring-adapter.md). The argument is mandatory (it cannot be forgotten), so for a public API you put `NoAuthCoordinator(context=Context())` explicitly. A single route can override it: `.post(path, Action, auth_coordinator=...)` — see [«What the base guarantees»](authoring-adapter.md#what-the-base-guarantees).
- **One mechanism — any transport:** the same coordinator serves HTTP, MCP, and your transport; `request_data` is what the specific adapter passes (a FastAPI request object, `None` for MCP).

## Verification

```bash
uv run python examples/how_to/02_custom_auth_coordinator.py
```

```text
valid key   -> ('agent_7', ['admin'], 'abc-1')
invalid key -> None
no creds    -> None
```

One coordinator assembled a `Context` with identity and roles from a valid key and returned `None` on an invalid one — the operation does not need to know about this entry mechanism. The whole concept, with the pipeline and review questions — [Step 12 — Authentication](../tutorials/step-12-authentication.md).

---

<table width="100%"><tr>
  <td align="left"></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"></td>
</tr></table>
