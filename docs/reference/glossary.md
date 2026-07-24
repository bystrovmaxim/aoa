<!-- translated-from: glossary_draft.md @ 2026-07-24T16:49:56Z (filesystem mtime; draft is gitignored, no git history) · sha256:fe7cf30eb8f9 -->
<p align="center">
  <img src="../assets/aoa-logo.png" alt="AOA" width="200">
</p>

# Glossary

<table width="100%"><tr>
  <td align="left"></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"></td>
</tr></table>

---

A brief reference of AOA terms — convenient to come back to while reading. The terms are grouped by layer: the operation core, execution, dependencies and resources, context and access, reliability, observability, the data model, testing, service. The precise rules and checks are in [Intents and invariants](intents-and-invariants.md), the formal notation is in [The formal model](formal-model.md).

---

## The operation core

**Action** — an atomic business operation cast as a class `BaseAction[Params, Result]`. Without state of its own between calls, read whole top to bottom. At the same time — a machine-readable specification of itself: roles, dependencies, steps, and contracts are available from the class without running.

**Aspect** — one step of an operation. A regular one (`@regular_aspect`) is intermediate, returns a `dict` that becomes the new `state`. The summary one (`@summary_aspect`) is the single terminal one, returns a `Result`. They execute strictly in declaration order in the class.

**Params** — the operation's typed input (a Pydantic model `BaseParams`, `frozen`). Only business data; no context, no transport.

**Result** — the operation's typed output (`BaseResult`, `frozen`). Returned from the summary aspect.

**state** — the pipeline's intermediate state: a sequence of **immutable snapshots** (`BaseState`, `frozen`). It lives only inside one call, does not outlive it, and does not accumulate on its own — each aspect explicitly returns the needed fields.

**Checker** (`@result_string`, `@result_int`, `@result_instance`, …) — a verifiable contract on an aspect's output: which field must appear in `state`, of which type, and with which constraints. A violation is a `ValidationFieldError` at the step boundary.

**Domain** (`BaseDomain`, `@meta(domain=...)`) — the logical area an operation or entity belongs to. The anchor of the system graph and the access matrix.

**`@meta`** — the operation's passport: description and domain. The description goes into external schemas and the graph, not staying a comment.

## Execution

**ActionProductMachine** — the executor. The single launch point: `machine.run(ctx, action, params)`. Checks roles, leads the pipeline, applies checkers, runs compensations and error handlers, calls plugins.

**Pipeline** — a linear sequence of aspects executed top to bottom without branches. A direct composition `summary ∘ aₙ ∘ … ∘ a₁`.

**box** — the instrument passed into every aspect. Through it: `box.info/warning/critical(...)` — business events; `box.resolve(T)` — dependencies; `box.run(Action, params)` — nested operations.

## Dependencies and resources

**`@depends`** — the declaration of a dependency service/operation in the header. Obtaining an undeclared dependency through `box.resolve(...)` is impossible.

**`box.resolve(T)`** — obtain the declared dependency `T` (the factory builds a new instance on each call; shared state is held through `@connection`).

**`box.run(Action, params)`** — launching a nested operation. The main composition mechanism: complex scenarios are assembled from small operations.

**`@connection`** — the declaration of an already-open resource (a connection, pool, client) the operation expects to receive. The machine checks the declared and supplied connections before the aspects launch.

**connections** — the dictionary of resources passed into a nested operation. On passing, the resource is wrapped in a proxy that forbids `commit`/`rollback`: a child operation does not control someone else's transaction.

**Resource** (`BaseResource`) — an adapter of the external world with long-lived state: a DB, an API, a queue, a payment gateway, a fixture. It contains transport, not business rules.

**Port and adapter** — an operation depends on an interface (a port), not on a concrete implementation (an adapter). A resource's implementation can be swapped without touching the logic.

## Context and access

**Context** — the call environment: user, request, runtime. Assembled before the operation runs; not visible to aspects whole.

**UserInfo / RequestInfo / RuntimeInfo** — parts of the context: user data (`user_id`, roles), request data (`trace_id`, path, method, IP), environment (`hostname`, `service_name`, runtime).

**ContextView** — the context slice an aspect receives via `@context_requires`. You cannot read an undeclared field through it.

**`@context_requires`** — the declaration of the context fields an aspect needs. Makes the consumption of the environment explicit.

**`@check_roles`** — the mandatory declaration of access. The machine checks roles before the first aspect; the absence of the decorator is an error.

**GuestRole / AnyRole / BaseRole** — `GuestRole` — open to everyone (explicitly); `AnyRole` — any authenticated; `BaseRole` — the root of domain roles, supports inheritance.

**AuthCoordinator** — builds `Context` from a transport request (credential extraction, verification, assembling the environment).

**`grant(role, when=...)`** — a role paired with an optional condition on the caller, inside `@check_roles`. Grants are tried in declaration order, `any()` semantics: a role matches and `when=` (if given) returns `True` — the role-level check passes. A bare role is equivalent to `grant(role)` with no condition.

**`guard=`** — a shared condition on `@check_roles`, one for every grant on the operation; checked once, after some grant has already won. Unlike `grant.when=(user)`, it also sees the call's parameters: `guard=(user, params)`.

**`access_decide`** — a method on `BaseAction`, the third, object-level access check (after role and `guard=`): `access_decide(self, params, context, box, connections) -> FailSecurityVerdict | AllowedVerdict`. Defaults to returning `AllowedVerdict()`. Denial is `AuthorizationError(level=3, verdict=...)`, the same error as at levels 1-2, carrying the same `FailSecurityVerdict` that `access_decide` returned.

**`BaseVerdict`** — the abstract root of the outcome of any access check (`aoa.action_machine.intents.access_control`); it cannot be instantiated directly (the constructor raises `TypeError`). `kind` is an ordinary field that `BaseVerdict.__init__` fills in and checks: omit `kind=` and it's set to `type(self).__name__`; pass one that doesn't match the class name and it raises `ValueError`. Defined once on the base class, inherited without redeclaration. Three concrete descendants:

- **`AllowedVerdict`** — success; there's no `reason` field at all — not an empty string, an absent field.
- **`FailSecurityVerdict`** — a genuine denial (role/`guard`/`access_decide` said "no"); `reason: str` is mandatory and non-empty.
- **`FailErrorVerdict`** — the check itself failed (an unknown endpoint, an unhandled exception on the check's path) — not a denial, and never cached as one.

Replaces the earlier `ResolveItemResult`/`AccessVerdict`/`ResolveItemKind` (a `StrEnum` of five values: `SUCCESS`/`SECURITY`/`FLAG`/`MACHINE_RULE`/`CHECK_ERROR`) and the validator function `kind_matches_reason` — the invariant "success ⟺ the reason is mandatory and non-empty" is now expressed by the class structure, with nothing left to check separately. The real instance goes straight into `ResolveResponse.results` (`list[SerializeAsAny[BaseVerdict]]`) — there's no separate translation step (`to_wire()`).

**`machine.check_access_decide`** — ask "would this be allowed?" without running the operation: the same role/`guard=`/`access_decide` cascade as `machine.run`, but without the pipeline, cache, or plugin events. The same overload accepts either one action or a list of `(action, params)` pairs — the list is the primary form, a single check is implemented as a one-item list.

## Reliability

**`@compensate`** — a compensator: how to roll back a specific regular aspect. On failure the machine calls the compensators in reverse order (stack unwinding). The pairing with the aspect is checked at startup.

**Saga** — a distributed transaction as a sequence of steps with compensations instead of a shared `try/finally`.

**`@on_error`** — the operation's global error handler: error types, order, fallback path — as a visible contract, a layer separate from the business logic and rollbacks.

**Cache** (`cache_key`, `on_cache_write`) — the operation declares what and under which conditions to cache; where to store and for how long is decided by the cache coordinator.

## Observability

**Plugin** — an observer of an operation's lifecycle. Receives events but does not affect execution; a plugin's failure does not bring down the operation.

**Lifecycle events** — start/finish, before/after an aspect, error, rollback — with the full surroundings (`params`, `state`, timings, nesting).

**Channel** — a business event's channel (`business`, `debug`, `security`, `compliance`, `error`; `client` — planned) for `box.info/...`; combined with `|`.

**Logger** — a recipient of `box` business events. Where to deliver (console, queue, Telegram) is decided by the logger, not the operation code.

**OpenTelemetry plugin** — traces and logs; `state` snapshots as `aoa.state.*` attributes. **OCEL** — an event log for process mining.

## The data model

**Entity** (`BaseEntity`, `@entity`) — a domain object: fields, relations, lifecycle. Without tables, sessions, and ORM mapping; one entity is assembled from various sources.

**Relations** — `Association` (equal), `Aggregation` (weak ownership), `Composition` (strong ownership); cardinality is set by the `One`/`Many` suffix. The reverse side is declared via `Inverse(...)` or explicitly absent via `NoInverse()`.

**Lifecycle** — a finite-state machine of an entity's states with correctness checked at build; a transition returns a new instance (the entity is immutable).

**Partial loading** — one domain type with different load levels. Touching an unloaded field is a `FieldNotLoadedError` / `RelationNotLoadedError`, not a silent `None`.

## Testing

**TestBench** — running an operation through the same machines with an assembled "world": context, `@depends` mocks, connections. The whole Action, one aspect, the summary, or a compensator is tested.

**rollup** — running a scenario against the production schema (real `INSERT`/`UPDATE`, a real pipeline) with a rollback on `commit`: a check without saving the changes.

## Service and meta

**Transport adapter** — `FastApiAdapter` (HTTP/REST + OpenAPI), `McpAdapter` (a tool for an AI agent), and others. One operation is available through any transport.

**params_mapper / response_mapper** — format translation at the adapter boundary, when the external schema diverges from the operation's contract (for example, v1/v2 API), without changing the operation itself.

**System graph** — the graph of operations, dependencies, resources, and entities built from the code; cycles and contracts are checked on it at startup.

**Maxitor** — the visualizer: builds an interactive graph, ERD, use-case, and FSM diagrams from the code.

**Machine-readable specification** — the property by which every `Action` describes itself (roles, dependencies, steps, contracts), and from this the documentation, the access matrix, and the diff of business intent between versions are assembled.

## UI permissions

**Resolver** — `POST /permissions/resolve` (`aoa-fastapi-adapter`). A thin HTTP wrapper around `machine.check_access_decide`: a list of `(operation, params)` → a list of results in the same order (`operation` is an endpoint identifier `"{method} {path}"`, e.g. `"POST /actions/cancel-order"`; if the route has a `params_mapper`, the resolver runs the incoming `params` through it before `access_decide`). Doesn't change or duplicate the access rule — it's still declared only via `@check_roles`/`access_decide` on the action itself. The list form deduplicates items that share the same `(operation, params)`: the real `access_decide` call happens once per distinct item, and `results` never gets shorter — duplicate positions get copies of the already-computed result.

**`AoaEngine`** — the framework-agnostic client core of the `aoa-client-js` package (`aoa-client-js/src/engine.ts`), the single entry point for asking the resolver questions. `resolve(items, opts?)` makes exactly one `POST /permissions/resolve` per call (no cache, no batching yet — those arrive in later chapters) and validates the response before trusting it: `res.ok`, content-type, `version`, `results` cardinality — failures at this level throw typed errors (`Unauthorized`/`ProtocolError`/`NetworkUnavailable`) instead of turning into a synthetic denial. Identity (`cachePartition`) is fixed at construction and never changes: switching subjects means a new `AoaEngine`, not mutating the old one. Every call carries its own `x-trace-id` (`crypto.randomUUID()` by default, overridable via `opts.traceId`). `fetchImpl` is injected as a constructor parameter (dependency injection) rather than read off `window.fetch` — so `AoaEngine` also runs in Node.js (SSR), not just the browser.

**`EndpointExecutionPlan` / `PreparedEndpointContext`** — one execution recipe for a single route (`aoa.fastapi.execution_plan`). `EndpointExecutionPlan` is an immutable pairing of "route + its effective `auth_coordinator`", built once at `build()`. `.prepare(request)` turns it into a `PreparedEndpointContext` — the `Context` and `connections` resolved for this one concrete request. Both the real endpoint and the resolver go through the same plan: there's no second way to get a `Context`/`connections` pair for a route, so `.can()` (the resolver) and `.run()` (the real call) physically cannot disagree about what's allowed. For a batch, the resolver calls `.prepare()` once per *distinct* `operation`, not once per item.

**`reason`** — the only substantive field on `FailSecurityVerdict`/`FailErrorVerdict` (on `AllowedVerdict` there's no such field at all — not an empty string): a non-empty, declared-ahead-of-time string. The same principle applies one layer down, as the mandatory companion of `when=`/`guard=`: `grant(role, when=..., reason=...)`/`check_roles(guard=..., reason=...)` take a `FailSecurityVerdict`, not a bare string. If `when=`/`guard=` is given without `reason=`, a default is substituted — `FailSecurityVerdict("FORBIDDEN_GRANT")`/`FailSecurityVerdict("FORBIDDEN_GUARD")` — a deliberate relaxation of the earlier rule (giving `when=`/`guard=` without `reason=` used to be a `ValueError`); the reverse case (`reason=` without `when=`/`guard=`) is still a `ValueError`. A role that never matched at all (no grant won) is the fixed `"FORBIDDEN_ROLE"`, not something the developer declares. One more fixed source the developer never declares — `"UNAUTHORIZED"` (`aoa-fastapi-adapter`): the route's own auth gate rejected the caller before the role/`guard`/`access_decide` cascade even started — a settled denial, not a check that was never reached, just with the route itself as the source instead of the action. `access_decide` (level 3) is no longer the exception: it returns `FailSecurityVerdict(reason=...)` with its own declared reason, same as the other levels.

**Role-gate** and **Object verdict** — a role-based check that ignores the specific object (RBAC, cascade levels 1-2: role and `guard=`), and a check based on a fact about a specific object (ABAC, level 3, `access_decide`), respectively. Indistinguishable on the wire today: both give the same `kind: "FailSecurityVerdict"` — a minimal oracle contract, a caller can't tell "no such object" from "exists, but not yours" from `kind` alone, only from the text of `reason`. Reporting them separately arrives together with object-level tags (`entities`) — a separate, not-yet-done piece of work.

**Subject** — whoever asks the resolver a question: an authenticated user, or a genuine anonymous guest (`NoAuthCoordinator`). Not to be confused with a role — a subject can hold zero, one, or several roles at once.

**`PermissionNamespace` / `cache_partition`** — an opaque label for the current identity, issued by `GET /permissions/namespace` (`{"cache_partition": "<opaque string>"}`), which the client attaches to every cached resolver answer so a cache can never end up mistakenly shared between two identities. Computed by `compute_cache_partition(context)` (`aoa-action-machine`, `aoa.action_machine.auth`) — a deterministic hash of `user_id` and the sorted set of role names; the same identity, right now, always maps to the same label, a different one always to a different one. Never on the manifest (it must stay identical for everyone, to remain cacheable and code-generatable) and never on the resolver's response (too late — the client needs the label before it can even look an answer up in its cache).

**`auth_epoch`** — a change of identity "generation": logging in as someone else, logging out, granting/revoking a role. Not implemented in AOA as a dedicated server-side counter (that would need session storage this stateless framework doesn't have) — instead, `cache_partition` is simply recomputed from the current identity on every call, and a change of identity produces a different label on its own. Revoking a still-unexpired token is the job of the `AuthCoordinator`/`Authenticator` in front of this function, not the function's own.

**Route shadowing** — two *different* path templates able to match the same real URL (`/users/me` next to `/users/{id}`, or `/users/{id}` next to `/users/{name}`). Not the same thing as an exact `(method, path)` duplicate — that's first-wins with a warning; route shadowing fails `FastApiAdapter.build()` entirely, via `RouteShadowError`, because Starlette's router still silently serves every real request to whichever was registered first, and without this check the manifest would list both, as if a client could choose. The check understands Starlette's typed converters (`{id:int}`, `{id:float}`, `{id:uuid}`, the greedy `{rest:path}`) and is deliberately conservative.

**Catalog** — the mechanism for publishing the endpoint list: `GET /client-manifest.json` (`aoa-fastapi-adapter`), a projection of already-registered HTTP routes (`self._routes`), not a walk over the action graph. Answers "what's registered," not "who can call it" — role-independent, identical for everyone who passed the entry gate. The HTTP layer publishes `ETag: "<manifest_version>"` (quoted) and `Cache-Control: private, no-cache`; a request with a matching `If-None-Match` gets back `304 Not Modified` with no body.

**Manifest** — the catalog's response body: `manifest_version`, `version`, `manifest_schema_version`, a list of `endpoints` (not `actions`), and `schemas`. Lists endpoints, not actions — one `action_class` on several routes yields several independent entries; an exact `(method, path)` duplicate is first-wins, not an error. A condition's body (`guard`/`when`/`access_decide`) structurally can't end up in it: the source is `FastApiRouteRecord` and the request/response models, and those functions' bodies simply aren't there.

**The manifest's three version numbers** — answer three different questions, and it's easy to conflate them. `version` — the resolver's wire-language version (the same number `POST /permissions/resolve` echoes; a mismatch is `400 unsupported_version`, checked before authentication). `manifest_schema_version` — the version of the manifest's own shape (these models); bumps only when the manifest's own field set/meaning changes, independent of `version` and of the currently-registered route set. `manifest_version` — a hash of the manifest's canonical content *without itself* (not an app version or a build date); published as the `ETag`. The graph is built once at process start, so `manifest_version` only changes between deploys — the manifest can be cached freely and cheaply revalidated via `If-None-Match` → `304`.

**`schemas`** — reference JSON Schemas (Draft 2020-12) for the protocol's own fixed messages, published under this manifest key: `ResolveRequest`, `ResolveResponse`, `BaseVerdict`, `ErrorEnvelope`, and the schema of `Manifest` itself. Every entry carries a `mode` — `"validation"` for `ResolveRequest` (the one thing the server validates on the way in) or `"serialization"` for everything the server only ever emits: the same pydantic model can produce a different schema depending on the mode. Doesn't replace each action's own `params_schema`/`result_schema` — this is a separate, closed set of the protocol's own messages.

**`ErrorEnvelope`** — the body of a *whole-request* failure (`400`/`401`/`403`/`5xx`): `{"error": {"code": "..."}}` (package `aoa.fastapi.permissions_schema`). Never used for a single batch item's problem — that stays a `CHECK_ERROR` inside a normal `200`. The only code today is `"unsupported_version"`.

**ManifestEndpoint** — one catalog entry: `operation` (`"{method} {path}"`), `name` (the class behind the endpoint — informational only), `domain`, `description`, `route` (`method`/`path`), `params_schema`/`result_schema` (from `model_json_schema()` of the corresponding models).

**`Primitive`** — the generated object for a single endpoint: statically, `generateClient(url)` from the separate `aoa-client-js/codegen` entry point; at runtime, `engine.loadFrom(url)`, a method on `AoaEngine` from the main `aoa-client-js` entry point, never from `codegen`. Either way, a thin wrapper over `AoaEngine` bound to that specific endpoint's parameter and result types. Up to three methods: `.verdict(params)` — the whole `Verdict`; `.can(params)` — a boolean question layered on top of it (`FailErrorVerdict` is thrown as `AoaResolveError`, not silently turned into `false`); `.run(params)` — the real invocation, whose call the library builds itself from the generated endpoint descriptor, with `actionInvoker` only executing the already-built call (it cannot substitute a different route or body). Not every `Primitive` has `.run()`: `createGateApi(engine)` builds a `GateApi` where `.run()` is absent at the type level, not merely unused; `createApi(engine, actionInvoker)` builds a `CallableApi` with the same `.verdict()`/`.can()` plus a working `.run()`. Layout in the `api` object is by full path always (`api.post["/actions/cancel-order"]`, an exact object with enumerated keys, not `Record<string, ...>`) plus a dot alias on a *clean* path (no `{param}`, hyphen, or dot, and no branch/leaf collision — e.g. `api.get.orders`) — both forms of access refer to the same `Primitive`, not two independent copies.

**Precheck** — a fresh, never-cached `can()` question that `Primitive.run()` asks itself right before the real invocation (`skipCache: true` on `AoaEngine.resolve()` — the only place in the library where this flag is used). Narrows the window between "the button was shown as allowed" and "the server actually checked" down to a single network round trip, instead of the cache's whole lifetime. Distinguishes a real, just-confirmed denial (`FailSecurityVerdict` — don't execute) from "couldn't ask" (`FailErrorVerdict`/a network error — not a denial, propagated as-is rather than turned into a synthetic "no"). The calling code doesn't need to know this second question ever happened: a denial looks like an ordinary error, with no dedicated class.

## Common errors

**ValidationFieldError** — a violation of an aspect's contract (no field, wrong type, broken constraint). **NamingSuffixError** — a name without the mandatory suffix. **CyclicDependencyError** — a cycle in the `@depends` graph. **MissingSummaryAspectError / MissingMetaError / MissingCheckRolesError** — a mandatory declaration is missing.

---

<table width="100%"><tr>
  <td align="left"></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"></td>
</tr></table>
