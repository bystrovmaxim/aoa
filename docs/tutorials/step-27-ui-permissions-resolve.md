<!-- translated-from: step-27-ui-permissions-resolve_draft.md @ 2026-07-19T17:51:39Z (filesystem mtime; draft is gitignored, no git history) · sha256:54e39377d13c -->
<p align="center">
  <img src="../assets/aoa-logo.png" alt="AOA" width="200">
</p>

# Step 27 — UI permissions: the resolver and the catalog

<table width="100%"><tr>
  <td align="left"><a href="step-26-maxitor.md">← Step 26 — Maxitor: a system you can see</a></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"><a href="../index.md">Contents →</a></td>
</tr></table>

- [The button that lies](#the-button-that-lies)
- [The idea: ask, don't copy the rule](#the-idea-ask-dont-copy-the-rule)
- [POST /permissions/resolve](#post-permissionsresolve)
- [One execution recipe: why .can() agrees with .call()](#one-execution-recipe-why-can-agrees-with-call)
- [A list is not a special case](#a-list-is-not-a-special-case)
- [A batch survives duplicates and one bad error](#a-batch-survives-duplicates-and-one-bad-error)
- [A guest is a valid answer too](#a-guest-is-a-valid-answer-too)
- [Whose question is this: PermissionNamespace and cache_partition](#whose-question-is-this-permissionnamespace-and-cache_partition)
- [The catalog: asking what's even possible](#the-catalog-asking-whats-even-possible)
- [The wire language's version, and the boundary of failure](#the-wire-languages-version-and-the-boundary-of-failure)
- [Why this isn't an ordinary operation](#why-this-isnt-an-ordinary-operation)
- [What the resolver doesn't say yet](#what-the-resolver-doesnt-say-yet)
- [Invariants](#invariants)
- [Check yourself](#check-yourself)

---

The [Authorization and roles](step-03-authorization-and-roles.md) chapter taught `@check_roles`/`access_decide` to decide "yes" or "no" on the server. But the frontend needs that same answer too — to decide whether the "Cancel order" button should be active or greyed out — and before this chapter it had no way to ask, other than trying the action and seeing whether the server refuses.

[▶ Try in Colab](https://colab.research.google.com/) · [Open in the project](../../examples/step_27_ui_permissions_resolve/01_role_gate_allowed.py)

---

## The button that lies

Picture an order table with a "Cancel" button on every row. The button can't be shown to everyone: only a manager can cancel an order, and not just any manager — one who actually has the right. Without a way to ask the server ahead of time, the frontend has exactly one path left: duplicate the same rule right inside the component:

```tsx
// BEFORE — the rule is manually duplicated
function OrderRow({ order, user }: { order: Order; user: CurrentUser }) {
  const canCancel = user.roles.includes("manager");
  return canCancel
    ? <button onClick={() => cancelOrder(order.id)}>Cancel</button>
    : <button disabled>Cancel</button>;
}
```

The rule "who can cancel an order" now lives in two places: on the server (the source of truth) and in the component (a copy). The server changes the rule — the component never finds out, until someone manually finds and fixes the copy.

---

## The idea: ask, don't copy the rule

Instead of keeping a copy of the rule, let the frontend ask the server directly — through a protocol, not by re-implementing the text of the rule. The server answers based on that one single rule, already declared via `@check_roles`/`access_decide`. There is no copy — so there can be no drift.

```tsx
// AFTER — the component doesn't know what the rule is made of
async function checkCanCancel(orderId: number): Promise<boolean> {
  const res = await fetch("/permissions/resolve", {
    method: "POST",
    body: JSON.stringify({
      version: 1,
      items: [{ operation: "POST /actions/cancel-order", params: { order_id: orderId } }],
    }),
  });
  const { results } = await res.json();
  return results[0].kind === "success";
}
```

The component doesn't contain a single word about roles. If the rule on the server changes, the component needs zero edits.

---

## POST /permissions/resolve

The endpoint itself is a thin wrapper around the already-existing `machine.check_access_decide` (see [Authorization and roles](step-03-authorization-and-roles.md#asking-first-machinecheck_access_decide)): the resolver adds no new authorization logic — it turns a list of `(operation, params)` into a list of answers in the same shape the machine already knows how to return.

```python
verdict = await machine.check_access_decide(manager, CancelOrderAction, OrderParams(order_id=7))
```

The resolver hands back exactly what `check_access_decide` returned, with no repacking: `BaseVerdict` (`aoa-action-machine`, `intents.access_control`) is the abstract root — `kind` isn't a separate field, it's the class's own name, computed (`type(self).__name__`). Three concrete outcomes: `AllowedVerdict` (success — there's no `reason` field at all), `FailSecurityVerdict` (a real denial — a role/`guard`/`access_decide` said "no"; `reason` is mandatory and non-empty), `FailErrorVerdict` (the check itself failed — an unrecognized endpoint, an unhandled exception; that's not a denial, and caching it as one would be wrong). The real instance goes straight into `ResolveResponse.results` — there's no separate translation step.

`AllowedVerdict` carries no `reason` — there's nothing more to say when nothing rejected the call. Full example — [`01_role_gate_allowed.py`](../../examples/step_27_ui_permissions_resolve/01_role_gate_allowed.py); on a denial — [`02_role_gate_denied.py`](../../examples/step_27_ui_permissions_resolve/02_role_gate_denied.py).

**`reason` is the mandatory companion of `when=`/`guard=` — but not a bare string.** A denial's reason isn't text the resolver invents after the fact — it's a `FailSecurityVerdict` the developer declared ahead of time. `grant(role, when=..., reason=...)`: give `when=`, and if you don't also give `reason=`, it defaults to `FailSecurityVerdict("FORBIDDEN_GRANT")`; you're free to supply your own `reason=`, but the reverse — `reason=` without `when=` — is still a `ValueError` at class declaration (there's nothing to explain if there's no condition). Exactly the same applies to `check_roles(..., guard=..., reason=...)`, defaulting to `FailSecurityVerdict("FORBIDDEN_GUARD")`. The `when=`/`guard=` contract itself (boolean functions) doesn't change.

```python
@check_roles(
    grant(ManagerRole, when=lambda user: user.department == "sales", reason=FailSecurityVerdict("not in sales")),
    guard=lambda user, params: params.amount < 10_000,
    reason=FailSecurityVerdict("amount too large"),
)
class ApproveDiscountAction(BaseAction[DiscountParams, DiscountResult]):
    ...
```

A role that never matched at all (none of the listed roles fit) isn't a declared case: here `reason` is the fixed string `"FORBIDDEN_ROLE"`, not something the developer writes. `access_decide` (level 3) is no longer the exception — it now returns its own `FailSecurityVerdict(reason=...)` with its own declared reason too, see [`05_guest_gated_by_event.py`](../../examples/step_27_ui_permissions_resolve/05_guest_gated_by_event.py).

One more fixed source the developer never declares — `"UNAUTHORIZED"`. A batch can mix operations across different routes, and each route can have its own `auth_coordinator=`. If a specific operation's own coordinator didn't let the caller through, that's not a failure of the whole request (other batch operations with their own coordinator can still go through fine) — it's `FailSecurityVerdict("UNAUTHORIZED")` at that operation's own position: a settled denial, not a check that never completed — the source is just the route itself, not the action's role/`guard`/`access_decide`.

**Run:**

```bash
uv run python examples/step_27_ui_permissions_resolve/01_role_gate_allowed.py
uv run python examples/step_27_ui_permissions_resolve/02_role_gate_denied.py
```

---

## One execution recipe: why .can() agrees with .call()

There's a tempting but dangerous way to implement the resolver: give it its own, lighter-weight authentication path — say, one fixed `auth_coordinator` for the whole request, ignoring the fact that a specific route may have declared its own (`auth_coordinator=` on `.post/.get/...`). Before this chapter, that's exactly how the resolver worked, and the real endpoint set up `Context`/`connections` its own way. The result: `.can()` (the resolver) and `.call()` (the real call) could honestly answer *differently* to the same question — if a route overrode the coordinator, or an `access_decide` read `connections`, the button could honestly say "yes" while the real call refused.

`EndpointExecutionPlan` is one execution recipe for a single route, built once at `build()`: the pairing of "route + its effective `auth_coordinator`" (a route override, or the adapter default). `PreparedEndpointContext` is what you get when you apply that plan to one concrete HTTP request: a ready `Context` and resolved `connections`. Both the real endpoint and the resolver go through the same `EndpointExecutionPlan.prepare(request)` — there is no second way to get a `Context`/`connections` pair for a route.

```
FastApiRouteRecord + effective_auth_coordinator
        │
        ▼
EndpointExecutionPlan (frozen, built once at build())
        │  .prepare(request)
        ▼
PreparedEndpointContext (per-request: Context + connections)
```

For a batch of several questions, the resolver doesn't call `.prepare()` per item — it calls it once per *distinct* `operation` in the batch, since authentication and connections don't depend on `params`. If a route doesn't override the adapter's default coordinator, the resolver reuses the `Context` it already got from its own entry gate, instead of authenticating the same request twice.

---

## A list is not a special case

`machine.check_access_decide` is one method with two shapes: a single action, or a list of `(action, params)` pairs. The list is not a side overload — it's the primary shape: a single check is implemented as a list of one item. That's why `POST /permissions/resolve` is list-shaped (`items`/`results`) from day one, even while the frontend still asks one question at a time — adding a second question to the same request later needs no change to the protocol's shape.

```python
single = await machine.check_access_decide(manager, CancelOrderAction, params)
batch = await machine.check_access_decide(manager, [(CancelOrderAction, params)])
# single.model_dump() == batch[0].model_dump()
```

**Run:**

```bash
uv run python examples/step_27_ui_permissions_resolve/03_batch_of_one_equals_single.py
```

---

## A batch survives duplicates and one bad error

A list of questions in one request is not a list of guaranteed *different* questions. An order table with "Cancel" and "Refund" buttons on every row is two independent frontend components, neither aware of the other; if both ask about the same order, the question `("POST /actions/cancel-order", {"order_id": 7})` can land in the batch twice. A naive implementation (a loop over `items`, a separate `access_decide` call for each) would do extra work in that case — the second call computes exactly the same thing the first one did, just once more.

`resolve_verdicts()` (package `aoa-fastapi-adapter`, `aoa.fastapi.permissions`) groups items by the key `(operation, canonical_key(params))` and calls `access_decide` exactly once per distinct key — at the position where that key was first seen, in request order, and the real calls for distinct keys run concurrently (`asyncio.gather`), not in a sequential loop. A batch of five questions where the first and the fifth are literally the same `(operation, params)`, and the three in between are different, produces **five** results in the response (the list never gets shorter — that's the same positional contract, `items[i]` ↔ `results[i]`, from the start of this chapter), but only **four** real `access_decide` calls: the fifth position gets an exact copy of the first position's result, computing nothing again.

```python
outcome = await resolve_verdicts(items, plan_index, prepared_by_operation, machine)
outcome.results           # always the same length as len(items) — even under full deduplication
outcome.real_call_count   # how many REAL access_decide calls happened — at most len(items)
```

`real_call_count` is not a wire-protocol field: the client has no business (and no need) knowing which positions were freshly computed and which were copied — from its point of view, every answer is equally honest and independent. The field exists for tests and for this chapter's examples — the one way to confirm deduplication actually happened, not so the frontend can rely on it.

The second, independent problem with the same naive approach is fragility to errors: one batch item with an unrecognized endpoint (a typo in the method or path, a stale frontend build) used to fail the whole request. Now that item gets `FailErrorVerdict(reason="UNKNOWN_ENDPOINT")` at its own position — the HTTP status is still `200 OK`, and the rest of the batch answers as usual. `FailErrorVerdict` is not a denial: the resolver never *decided* "no" — it never reached a decision at all, and caching such an answer as "no" would be a lie (see `BaseVerdict` above).

```python
{"kind": "FailErrorVerdict", "reason": "UNKNOWN_ENDPOINT"}
```

**Run:**

```bash
uv run python examples/step_27_ui_permissions_resolve/06_duplicate_within_batch.py
uv run python examples/step_27_ui_permissions_resolve/07_unknown_action_in_batch.py
uv run python examples/step_27_ui_permissions_resolve/09_mixed_dedup_isolation_and_order.py
```

---

## A guest is a valid answer too

The resolver always calls `auth_coordinator.process(request)` — but that isn't the same thing as "only works for logged-in users." If the coordinator (e.g. `NoAuthCoordinator`) answers missing credentials with a real anonymous `Context` rather than `None`, the resolver proceeds into `machine.check_access_decide` as usual — and an action with `@check_roles(GuestRole)` gets an honest `AllowedVerdict`, exactly like any other role. `403` only happens when `process()` genuinely returned `None`.

```python
guest = Context()  # anonymous, but a real Context — not None
verdict = await machine.check_access_decide(guest, BrowseCatalogAction, PublicParams())
```

`GuestRole` only clears the question itself — it doesn't mean "always `AllowedVerdict`". `access_decide` (level 3) can still base its answer on any fact, not just object ownership — for example, on whether a real-world event has already happened.

```python
async def access_decide(self, params, context, box, connections) -> FailSecurityVerdict | AllowedVerdict:
    order = orders_db[params.order_id]
    if order.tracking_token != params.tracking_token:
        return FailSecurityVerdict("tracking token does not match this order")
    if order.status in ("shipped", "in_transit", "delivered"):
        return AllowedVerdict()
    return FailSecurityVerdict("order has not shipped yet")  # event hasn't happened yet — too early
```

**Run:**

```bash
uv run python examples/step_27_ui_permissions_resolve/04_guest_role_vs_rejected_anonymous.py
uv run python examples/step_27_ui_permissions_resolve/05_guest_gated_by_event.py
```

---

## Whose question is this: PermissionNamespace and cache_partition

A client that caches resolver answers (so it doesn't have to ask "can order 7 be cancelled" all over again on every render) must be able to tell: whose "yes" is this cached answer for? The client itself can't safely construct that answer from a value it already holds (a stale variable, a key built before an account switch actually took effect) — only the server reliably knows who's asking *right now*.

`GET /permissions/namespace` returns `{"cache_partition": "<opaque string>"}` — an opaque label for the current identity, which the client attaches to every cached resolver answer. The label is opaque: the client never parses or reconstructs it, it just carries it along. It's deterministic: the same identity, right now, always maps to the same label; a different identity — a different `user_id`, or the same user with a different set of roles — always maps to a different one.

```python
def compute_cache_partition(context: Context) -> str:
    roles = ",".join(sorted(role.name for role in context.user.roles))
    identity = f"{context.user.user_id or ''}|{roles}"
    return hashlib.sha256(identity.encode()).hexdigest()
```

A change of identity "generation" (`auth_epoch` — logging in as a different user, granting or revoking a role) doesn't need a dedicated generation counter on the server in AOA: this stateless framework has no session storage that such a counter would have to stay in sync with. Instead, the label is simply **recomputed from the current identity on every call** — a different `user_id` or a different role set hashes to a different string on its own, for free, with no state to keep in sync. Logging out has no label at all — there's no authenticated `Context` to compute one from. Revoking a still-unexpired token isn't something this formula can detect on its own — that's the job of the `auth_coordinator` standing in front of it (a revocation check that makes `process()` return `None`) — once the coordinator has rejected a revoked identity once, there is never again a `Context` or a label for it.

`cache_partition` is deliberately not on the manifest (it must stay identical for everyone to stay cacheable and code-generatable) and not on the resolver's response (too late — the client needs the label *before* it can even look an answer up in its cache).

---

## The catalog: asking what's even possible

The resolver answers "can I call *this specific* endpoint?" But to ask the question, the frontend has to already know that the endpoint exists at all, and that its `operation` is exactly `"POST /actions/cancel-order"`, not `/cancel` or `/order-cancel`. Right now the only source of that knowledge is a Slack thread and a hardcoded string — the exact stub string that silently breaks when the backend renames a path.

The catalog removes that string. The server publishes `GET /client-manifest.json` — a machine-readable list of every endpoint it exposes: its `operation`, its HTTP route, the schemas of its params and result, and (see below) the protocol's own reference schemas.

```json
{
  "manifest_version": "sha256:fdeb4445...",
  "version": 1,
  "manifest_schema_version": 2,
  "endpoints": [
    {
      "operation": "POST /actions/cancel-order",
      "name": "CancelOrderAction",
      "domain": "StoreDomain",
      "description": "Cancel an order",
      "route": { "method": "POST", "path": "/actions/cancel-order" },
      "params_schema": { "type": "object", "properties": { "order_id": { "type": "integer" } }, "required": ["order_id"] },
      "result_schema": { "type": "object", "properties": { "status": { "type": "string" } } }
    }
  ],
  "schemas": {
    "ResolveRequest": { "mode": "validation", "json_schema": { "...": "JSON Schema Draft 2020-12" } },
    "ResolveResponse": { "mode": "serialization", "json_schema": { "...": "..." } },
    "BaseVerdict": { "mode": "serialization", "json_schema": { "...": "..." } },
    "ErrorEnvelope": { "mode": "serialization", "json_schema": { "...": "..." } },
    "Manifest": { "mode": "serialization", "json_schema": { "...": "..." } }
  }
}
```

**The catalog is a projection of already-registered routes, not a walk over the action graph.** Every `adapter.post/get/...(path, ActionClass)` places a `FastApiRouteRecord` in `self._routes`; `build()` creates the real endpoints from that same list. The catalog just serializes what's already there: `operation` (`method`+`path` joined), `route`, and `model_json_schema()` of `effective_request_model`/`effective_response_model`. Walking the whole action graph isn't necessary — and it wouldn't be right either: the graph would also hand back actions that are never exposed at all (only ever called internally via `box.run()`), which have no business being in the catalog.

Which leads to the key property: **the manifest lists endpoints, not actions.** The same class can be registered on several paths (API versions via `params_mapper`), and each registration is an independent endpoint with its own `operation`. That's why `operation` in `POST /permissions/resolve` is `"{method} {path}"`, not a class name: an endpoint's address is unique by (method, path); which Python class sits behind it is the server's own business (it's on `name`, informationally only).

What the catalog does **not** do:

- **It doesn't look at roles.** It answers "what's registered," not "who can call it" — the resolver already answers the second question. So the manifest is identical for everyone who passed the entry gate, including an honest guest via `NoAuthCoordinator`. `403` only happens if `auth_coordinator.process()` returned `None`.
- **A condition's body can't leak into it.** Neither `guard=`, nor `when=`, nor `access_decide` can end up in the manifest — and that's not a separate filter: it's built from `FastApiRouteRecord` (method, path, class, request/response models), and those functions' bodies simply aren't part of a route record.

### Route uniqueness and shadowing

Two different routes can genuinely accept the same URL — and Starlette's router always silently serves such a request to whichever was registered first, never raising an error. The catalog and the resolver must agree with that behavior, not diverge from it:

- **An exact duplicate** — the same `(method, path)` registered twice — is not an error: the first registration wins (`first-wins`), exactly like the real router (the second is unreachable anyway). Deduplication happens **before** `manifest_version` is computed, so the hash reflects the real, already-deduplicated content. Registering an exact duplicate produces a `UserWarning` right when `.post/.get/...(...)` is called — not fatal, but noticeable.
- **Route shadowing** — two *different* templates that could match the same URL (`/users/me` next to `/users/{id}`, or `/users/{id}` next to `/users/{name}`) — is not a duplicate, it's a trap: the router still sends every real request to whichever was registered first, but the manifest would list *both*, as if the client could choose. `FastApiAdapter.build()` fails on this with `RouteShadowError` — at build time, not at runtime. The check understands Starlette's typed converters (`{id:int}`, `{id:float}`, `{id:uuid}`, and the greedy `{rest:path}`, which can absorb any number of trailing segments including slashes) and is deliberately conservative: a literal segment rules out a collision with a typed converter only when it clearly can't satisfy it (`/items/latest` next to `/items/{id:int}` is fine; `/items/42` next to the same is a conflict).

### The manifest's HTTP contract: cheap to cache, never silently stale

`manifest_version` is a hash of the manifest's canonical content *without itself* — hashing a field that would then have to contain its own hash is a circle with no fixed point, so it's computed first, then inserted. The action graph is built once at process start and never changes at runtime, so the hash only changes between deploys. The HTTP layer publishes it as `ETag: "<manifest_version>"` — quoted, as the ETag spec requires — together with `Cache-Control: private, no-cache`. "`private`" here doesn't mean the body differs per caller (it's identical — role-independent and identity-neutral for anyone who passed the entry gate) — it means the response depends on successful authentication at all; "`no-cache`" means the client must always revalidate rather than silently serve a stale catalog. A request with a matching `If-None-Match` (an exact match, or `*`) gets back `304 Not Modified` with the same headers and no body, instead of the whole manifest again.

The manifest's three separate numbers answer three different questions, and it's easy to conflate them:

- **`version`** — the resolver's wire-language version (the same number `POST /permissions/resolve` reads on the way in and echoes on the way out — see the next section).
- **`manifest_schema_version`** — the version of the manifest's own shape (these models). Bumps only when the manifest's own field set/meaning changes — independent of `version` and of how many routes happen to be registered right now.
- **`manifest_version`** — the content hash described above; this is exactly what the server publishes as the `ETag`.

### Reference schemas (`schemas`)

A client that wants to genuinely *validate* what it sends and receives needs an authoritative shape for every fixed protocol message — not each action's own `params_schema`/`result_schema` (already on every `endpoints` entry), but `ResolveRequest`, `ResolveResponse`, `BaseVerdict`, the error envelope (`ErrorEnvelope`), and the catalog's own shape. The manifest publishes all of these under one key, `schemas` — the reference never has to be guessed. `BaseVerdict` is abstract, and its own published schema shows only `{kind}` — that's a guaranteed minimum, not a closed shape; a real item (`AllowedVerdict`/`FailSecurityVerdict`/`FailErrorVerdict`) also carries `reason`, except for `AllowedVerdict`, which doesn't have one at all.

Two details that matter. The dialect is **JSON Schema Draft 2020-12** (each schema carries its own `$schema`), in a small, agreed-on subset: plain types, lists, enums, in-document `$ref`s — no recursive types, no homegrown formats. And the mode: the same pydantic model can produce a different schema for *validating* an incoming request than for *serializing* an outgoing response (for instance, whether a field with a default is required differs between the two). So every entry carries its own `mode`: `"validation"` — only for `ResolveRequest` (the one message the server actually validates on the way in) — or `"serialization"` — for everything the server only ever emits, including `Manifest` itself: a client can validate the very catalog it just received against a schema published inside that same catalog.

**Run:**

```bash
uv run python examples/step_27_ui_permissions_catalog/01_registered_action_in_manifest.py
uv run python examples/step_27_ui_permissions_catalog/06_same_action_multiple_endpoints.py
uv run python examples/step_27_ui_permissions_catalog/07_route_shapes_to_operation.py
```

---

## The wire language's version, and the boundary of failure

The resolver's "question and answer" language has its own version number — `version`, the same one the manifest publishes. The client always sends the version it was built for; the resolver checks it **first, before authentication** — a client speaking the wrong language shouldn't have to prove its identity first just to be told to upgrade. A mismatch is a `400` with body `{"error": {"code": "unsupported_version"}}` (`ErrorEnvelope`, the same envelope published under `schemas`).

This is a specific case of a general rule that's already come up piece by piece in this chapter — now it can be stated whole. If the whole request is fundamentally invalid — the wrong wire-language version (`400`), the caller has no right to poke the resolver at all (`403`, `auth_coordinator.process()` returned `None`), or something broke on the server's own side (`5xx`) — the **whole request** fails, with not a single answer in it at all. Only if the request clears that bar does the default of a partial answer kick in: a single batch item that didn't check out becomes a `FailErrorVerdict` at its own position (see the batch section above), while every other item answers as usual. One bad position doesn't sink the batch — but only *after* the whole request has already been judged sound.

---

## Why this isn't an ordinary operation

The resolver needs to ask the machine about *other* actions — dozens per call, without running a single one of them. An ordinary AOA action runs inside a `ToolsBox`, which, by the context-privacy invariant, holds no reference to either `machine` or a full `Context` at all (see the `tools_box.py` docstring). So the resolver can't be an ordinary `BaseAction` registered via `.post(action_class)` — it needs direct access to `self._machine`/`self._auth_coordinator`, which only the adapter itself has.

The solution is a bespoke route registered right inside `FastApiAdapter.build()`, next to the already-existing `_register_health_check` (the `GET /health` endpoint) — except, unlike that one, it never skips the `auth_coordinator.process()` call. The catalog and `GET /permissions/namespace` from the previous sections are the same case: the catalog needs `self._routes`, which an ordinary action can't reach either, and `/permissions/namespace` isn't about an action at all — it's about the caller's own identity — so all three are registered right there.

---

## What the resolver doesn't say yet

This chapter is the base: role level (1-2) and object level (3) via `access_decide`, a list from day one, guest access, deduplication and per-item error isolation, one execution recipe, cache partitions, route shadowing, HTTP caching for the catalog, and wire-language versioning. Deliberately out of scope:

- **Honest reporting of the object-level check.** Role-level and object-level checks are still indistinguishable on the wire in this chapter — both produce the same `kind: "FailSecurityVerdict"` (a minimal oracle contract: a caller can't tell "no such object" from "exists, but not yours" from `kind` alone — only from the text of `reason`). Revealing that detail is safe only together with generic deny — the same answer for "no such object" and "exists, but not yours"; without it, revealing the detail would hand an attacker a way to guess other people's object IDs from the shape of a denial. This mechanism arrives in chapter 8. Future channels like a disabled feature or a triggered operational rule are a separate, unrelated piece of future work; in this architecture each such channel will be its own subclass of `FailSecurityVerdict`, not a pre-reserved enum value.
- **The client package.** This chapter's examples call `machine.check_access_decide`/the resolver directly; a convenient typed client (`api.post["/actions/cancel-order"].can(...)`) doesn't exist yet.

---

## Invariants

- **The resolver doesn't change the machine.** Route registration is a thin wrapper in `aoa-fastapi-adapter`; the access rule is still declared only via `@check_roles`/`access_decide` on the action itself.
- **A list is the primary shape.** A single question is a batch of one, not a separate code path; `POST /permissions/resolve` accepts and returns lists (`items`/`results`) from day one.
- **`.can()` and `.call()` share one recipe.** Both go through the same route's `EndpointExecutionPlan.prepare(request)` — there is no second way to get a `Context`/`connections` pair, so the two physically cannot disagree.
- **`auth_coordinator.process()` is always called.** `403` only if it returned `None`; a resolved anonymous `Context` (`NoAuthCoordinator`) flows into the machine as usual.
- **`kind` is always present, `reason` is present except on success.** `kind` is the outcome class's own name (`BaseVerdict` and its three concrete subclasses). `AllowedVerdict` carries no `reason` at all; `FailSecurityVerdict`/`FailErrorVerdict` carry a non-empty, declared-ahead-of-time string. `FailErrorVerdict` is not a denial and must never be cached as one.
- **`reason` is a declaration, not a guess made after the fact.** A `when=`/`guard=` that can reject must carry its own `FailSecurityVerdict` — leave it unset and it defaults to `FailSecurityVerdict("FORBIDDEN_GRANT")`/`FailSecurityVerdict("FORBIDDEN_GUARD")`. A role that never matched at all is the fixed `"FORBIDDEN_ROLE"`; a route's own auth gate rejecting a single batch item is the fixed `"UNAUTHORIZED"`. Neither one is declared by the developer.
- **A duplicate is about work, not about the answer.** Items with the same `(operation, params)` produce `results` of the same length and order; only the number of real `access_decide` calls is saved (counted only for the first occurrence of a key), never the length of the response.
- **One bad item never sinks the batch — but only inside an already-valid request.** An unrecognized endpoint — `FailErrorVerdict(reason="UNKNOWN_ENDPOINT")` at its own position, `200 OK` for the whole request. A structurally invalid whole request — the wrong wire-language version (`400`), a failed entry gate (`403`), a server-side failure (`5xx`) — sinks everything, with not a single answer in it.
- **The resolver, the catalog, and `/permissions/namespace` are bespoke routes, not actions.** Registered directly in `FastApiAdapter.build()`, because an ordinary action can't reach `machine`, a full `Context`, or `self._routes`.
- **The catalog lists endpoints, not actions.** `GET /client-manifest.json` is a projection of `self._routes` (the `endpoints` field); `operation` = `"{method} {path}"`. One `action_class` on several routes is several independent entries; an exact `(method, path)` duplicate is first-wins with a warning, not an error.
- **Route shadowing fails the build.** Two different templates able to match the same URL — `RouteShadowError` at `build()`, not a silent mismatch between the catalog and the real router.
- **The manifest is role-independent, identity-neutral, and can't leak.** Identical for everyone who passed the entry gate (including a guest via `NoAuthCoordinator`); a condition's body (`guard`/`when`/`access_decide`) structurally can't end up in it.
- **The manifest's three numbers answer three different questions.** `version` (the resolver's wire language), `manifest_schema_version` (the manifest's own shape), `manifest_version` (a hash of content without itself, published as the `ETag`).
- **`cache_partition` is recomputed, not stored.** A deterministic function of the current identity (`user_id` + sorted roles) — a change of identity produces a new label on its own, with no server-side generation counter.
- **An unsupported wire-language version fails the whole request too.** `version` is checked before authentication; a mismatch is `400 unsupported_version`, the same error envelope (`ErrorEnvelope`) published under `schemas`.

---

## Summary

`POST /permissions/resolve` is a thin, but principled, layer over `machine.check_access_decide`: the frontend gets an honest "can I?" from the one place the rule is declared, instead of keeping a copy of the rule in the component. A list is the protocol's primary shape from day one; a guest isn't a special case for the resolver, but an ordinary role checked by the same cascade; one `EndpointExecutionPlan` keeps `.can()` and `.call()` from ever disagreeing. The batch, meanwhile, is resilient to its own duplicates (identical questions cost one real call but never shorten the response) and to one bad error (an unrecognized action only quenches its own position, not the whole request) — but not to a request that's invalid as a whole: the wrong wire-language version, a failed entry gate, or a server-side failure still take everything down. The catalog removes the hardcoded stub string, publishes the protocol's own reference schemas, and caches cheaply via `ETag`/`304` without fear of shadowing between routes; `cache_partition` gives the client a way to never mistake someone else's cached answer for its own.

---

## Check yourself

1. What's the difference between `FailSecurityVerdict` and `FailErrorVerdict`? Why can't the second one be cached as a denial?
2. What's the difference between "`auth_coordinator.process()` returned `None`" and "returned an anonymous `Context`"? What does the resolver do in each case?
3. Why does `POST /permissions/resolve` accept a list from day one, even though the frontend currently sends one item at a time?
4. Why can't the resolver be an ordinary `BaseAction` registered via `.post(action_class)`? What access, specifically, does an ordinary action lack?
5. What, exactly, could diverge between `.can()` and `.call()` before `EndpointExecutionPlan`, and why does one shared `.prepare(request)` for both paths close that gap?
6. An action's `access_decide` returned `FailSecurityVerdict` for a guest. Does that mean the guest doesn't own the object? Give another possible reason for the denial.
7. A batch of five questions where the first and the fifth are the same `(operation, params)`. How many items will `results` contain? How many times will `access_decide` actually run?
8. Why isn't `real_call_count` published on the wire `BaseVerdict`, even though it exists on `ResolveOutcome`?
9. Why is `operation` in `POST /permissions/resolve` `"{method} {path}"`, rather than an action class name? What would become ambiguous if `operation` were a class name and one class were registered on two paths?
10. Why is the catalog built from `self._routes`, rather than by walking the whole action graph? What would end up in the manifest from a graph walk that shouldn't be there?
11. What's the difference between an exact `(method, path)` duplicate and route shadowing? Why is one a warning and the other a build failure?
12. `grant(role, when=...)` without `reason=` — what happens, and exactly when (at class declaration, or on the first real request)?
13. Why isn't `cache_partition` stored on the server as a generation counter, but recomputed on every call instead? What would go wrong on logout if the formula weren't recomputed?
14. A client sends `version: 2`; the server only understands `version: 1`. Walk through what happens, step by step — and why this check runs before authentication, not after it.
15. Why is `manifest_version` hashed without itself? What would go wrong if the field hashed its own value too?

> **Exercise.** Take `TrackOrderAction` from [`05_guest_gated_by_event.py`](../../examples/step_27_ui_permissions_resolve/05_guest_gated_by_event.py) and add a second reason for denial to `access_decide` — for example, that the tracking code is only valid for 30 days after shipping. Run `machine.check_access_decide` before shipping, after shipping, and after the 30 days have passed, and confirm `kind`/`reason` reflect exactly that reason in each case.

---

<table width="100%"><tr>
  <td align="left"><a href="step-26-maxitor.md">← Step 26 — Maxitor: a system you can see</a></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"><a href="../index.md">Contents →</a></td>
</tr></table>
