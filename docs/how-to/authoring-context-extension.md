<!-- translated-from: authoring-context-extension_draft.md @ 2026-06-17T11:39:51Z · sha256:c995c285d60f -->
<p align="center">
  <img src="../assets/aoa-logo.png" alt="AOA" width="200">
</p>

# Extending Context

<table width="100%"><tr>
  <td align="left"></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"></td>
</tr></table>

- [When this is needed](#when-this-is-needed)
- [Three parts and the contract](#three-parts-and-the-contract)
- [Step 1. Extend a part by inheritance](#step-1-extend-a-part-by-inheritance)
- [Step 2. Build it in the coordinator](#step-2-build-it-in-the-coordinator)
- [Step 3. Read it in an aspect](#step-3-read-it-in-an-aspect)
- [What is important to know](#what-is-important-to-know)
- [Verification](#verification)

---

## When this is needed

`Context` carries the call environment: who is calling, the request trace, runtime metadata. When you need **your own** fields — `tenant_id`, an API version, a deployment region, a tenant identifier — you extend the corresponding part. The whole Context concept — [Step 7 — Context](../tutorials/step-07-context.md); here is how to add your own to it.

The full example: [07_extend_context.py](../../examples/how_to/07_extend_context.py).

## Three parts and the contract

`Context` (frozen, `extra="forbid"`) consists of three parts, and **each** of them is extended:

- `user: UserInfo` — identity and roles;
- `request: RequestInfo` — request metadata (trace, path, IP, protocol);
- `runtime: RuntimeInfo` — environment metadata (host, service, version, pod).

`Context` itself adds no fields (it is `extra="forbid"`) — you extend a **part**, by inheritance with explicit fields. Aspects meanwhile never touch `Context` directly: they declare the needed paths via `@context_requires` and receive a `ContextView`.

## Step 1. Extend a part by inheritance

Subclass the needed part and add explicit fields. All three can be extended this way:

```python
from aoa.action_machine.context.user_info import UserInfo
from aoa.action_machine.context.request_info import RequestInfo
from aoa.action_machine.context.runtime_info import RuntimeInfo

class TenantUserInfo(UserInfo):
    tenant_id: str = ""

class VersionedRequestInfo(RequestInfo):
    api_version: str = "v1"

class DeployRuntimeInfo(RuntimeInfo):
    region: str = ""
```

The fields are **explicit** (declared), not "extra": the parts are `extra="forbid"`, so arbitrary keys cannot be put there, but inheritance with typed fields is the sanctioned path.

## Step 2. Build it in the coordinator

`Context` is born at the boundary — it is assembled by the [authentication coordinator](authoring-auth-coordinator.md). That is where the extended parts go:

```python
ctx = Context(
    user=TenantUserInfo(user_id="u-42", tenant_id="acme"),
    request=VersionedRequestInfo(api_version="v3"),
    runtime=DeployRuntimeInfo(region="eu-central"),
)
```

The `Context` fields are typed by the base classes, but pydantic keeps the passed instance **as is** — `ctx.user` will stay `TenantUserInfo`, and `tenant_id` is not lost. (In the example above the coordinator is replaced with direct assembly for brevity; in production the parts are filled by `ContextAssembler` / `Authenticator`.)

## Step 3. Read it in an aspect

An aspect declares the paths it needs. For standard fields — the `Ctx.*` constants (IDE autocomplete), for your own — **raw string paths** (`"user.tenant_id"`):

```python
from aoa.action_machine.context import Ctx
from aoa.action_machine.intents.context_requires.context_requires_decorator import context_requires

@summary_aspect("Read environment")
@context_requires(Ctx.User.user_id, "user.tenant_id", "request.api_version", "runtime.region")
async def whoami_summary(self, params, state, box, connections, ctx):
    tenant = ctx.get("user.tenant_id")
    region = ctx.get("runtime.region")
    ...
```

`@context_requires` adds a sixth parameter `ctx` (a `ContextView`) to the aspect, and it returns values via `Context.resolve(path)`. A path the aspect **did not declare** cannot be read — `ContextView` refuses, even if the field is in the context. So business logic does not grow onto the transport.

## What is important to know

- **The subclass survives assignment.** The `Context.user` field is typed `UserInfo`, but pydantic does not "trim" the instance to the base — `TenantUserInfo` and its `tenant_id` are preserved (proven in the [example](../../examples/how_to/07_extend_context.py): `ctx.user is TenantUserInfo`).
- **`Ctx.*` covers only standard fields.** Your own are read by a raw path `"part.field"` — the same one `Context.resolve()` understands. `@context_requires` does not check path existence at registration (the context schema is extensible); a typo returns an empty value, not an error.
- **Access only to the declared.** `ContextView` returns only the paths listed in `@context_requires`; anything else — `ContextAccessError`. The aspect does not see the whole `Context`.
- **`None` is normalized to a default.** `Context(user=None)` gives `UserInfo()`; `ctx.user/request/runtime` are never `None` — which means the extended parts can be supplied as `None` too, the coordinator will not fail.

## Verification

```bash
uv run python examples/how_to/07_extend_context.py
```

```text
ctx.user is TenantUserInfo -> acme
user=u-42 tenant=acme api=v3 region=eu-central
```

All three parts are extended with their own fields, the subclass instances are preserved, and the aspect read both standard and custom fields through the declared paths. The whole Context concept, with review questions — [Step 7 — Context](../tutorials/step-07-context.md).

---

<table width="100%"><tr>
  <td align="left"></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"></td>
</tr></table>
