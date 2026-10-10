<!-- translated-from: glossary_draft.md @ 2026-07-16T21:46:23Z (filesystem mtime; draft is gitignored, no git history) · sha256:20a442b8bfcd -->
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

**`grant(role, when=..., reason=...)`** — a role paired with an optional condition on the caller, inside `@check_roles`. Grants are tried in declaration order, `any()` semantics: a role matches and `when=` (if given) returns `True` — the role-level check passes. A condition **must declare the reason it refuses with** (`reason=`, and `guard_reason=` for the shared condition): the sentence travels into `Refused.reason`, and a refusal caused this way names the step `WHEN`, not `CHECK_ROLES`. A bare role is equivalent to `grant(role)` with no condition.

**`guard=`** — a shared condition on `@check_roles`, one for every grant on the operation; checked once, after some grant has already won. Unlike `grant.when=(user)`, it also sees the call's parameters: `guard=(user, params)`.

**`@access_decide`** — the declaration of an operation's object-level rule, beside `@check_roles` in the header: a method named `..._access_decide`, `async`, with a required non-empty description, at most one per operation and never inherited. Its signature is fixed — `(self, params, box, connections)`, plus the trailing `ctx: ContextView` that `@context_requires` adds — and it answers with a **verdict**. The description and the declared context keys travel into the assembled graph, where the check is a node of its own type.
**`Verdict`, `Allowed`, `Refused`, `Undecided`** — the answers to "may I?", and there are exactly three. `Refused` and `Undecided` name the step that answered, through `gate`; only `Refused` may carry a `reason`, and only when the developer declared one. `Undecided` carries the step alone — never the failure's text.
**The five words** — `AUTH_COORDINATOR`, `CHECK_ROLES`, `WHEN`, `GUARD`, `ACCESS_DECIDE`: the steps of the cascade, and the value of `gate` on a refusal. `WHEN` is a role's own condition refusing while the role matched; `GUARD` is the operation's shared condition.
**`AccessDenied`, `AccessUndecided`** — what the executing path raises instead of returning: `AccessDenied(verdict)` carries the refusal, `AccessUndecided(verdict)` is raised `from` the original failure and says only which step could not decide. A refusal is an answer; a failure is not.
**`FORBIDDEN_OBJECT`** — the framework's refusal for an object-scoped check: "there is no such object, or it is not yours" in one answer, so the error channel cannot be used to enumerate what exists.
**`machine.check_access_decide`** — ask "would this be allowed?" without running the operation: the same cascade as `machine.run`, without the pipeline, the cache or the lifecycle events. One call, one answer, always one of the three words — a refusal here is an answer, not an exception.



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

**Relation container** — an object holding a reference to another entity separately from that entity's loaded data. Ownership containers use `One` or `Many`; specialization uses `Specialization[T]` and its reverse `Generalization[T]`. Their loading interfaces differ, so consult the particular container's contract.

**Specialization** — a declared relationship between common information and the different kinds of details that may accompany it. For example, common record information may have first-pressing, re-pressing, or test-pressing details. The common class declares a `Specialization` field listing these alternatives. It describes possible types, not an automatic loading operation.

**Head** — the class holding the common information and declaring a specialization field. `VinylRecordEntity` is the head in the tutorial: it holds the title and the link to pressing details.

**Alternative / variant / extension** — one of the detail classes listed by a specialization field. `FirstPressEntity` is an alternative because it holds information specific to a first pressing. It declares its own code and a reverse link to the head; it need not be a Python subclass of that head.

**Classifier field** — the head's ordinary data field whose value identifies the kind of details, such as `media="first"`. On the head, `Classifier(field="media", codes=Literal["first", "repress", "test"])` names this field and declares the codes. On an alternative's reverse link, a `Classifier` marker declares that alternative's single code.

**Variant code** — an application-chosen string such as `first` that identifies an alternative in the declaration. It is not the class name. The head lists the codes and each alternative declares its own; the build compares those declarations. That comparison does not validate every code supplied in instance data.

**Specialization axis** — one specialization field together with its classifier and alternatives. The name distinguishes multiple choices on one head, such as `pressing` and `reported_pressing`. The current validator restricts which multiple-axis arrangements are accepted.

**Generalization** — for entity specialization, the reverse direction from specific details to the common entity. `Generalization[VinylRecordEntity]` holds a reference back to the record. The associated graph edge uses the `Generalization` relationship; this does not make the two Python classes inherit from one another.

**Inverse relation** — the other declared direction of a relationship. `Inverse(Target, "field")` names the paired field. A specialization head can use `Inverse(field_name="record")`, since its possible target classes are already listed in the type argument.

**Hydration** — supplying an entity's actual data in memory after identifying it. For a specialization link, passing an object as `entity=...` makes that object available through `.entity`; omitting it leaves `.entity` as `None`. The container itself performs no loading.

**Model build** — assembling and checking AOA's graph of the loaded declarations, normally during machine creation. It checks the model, not stored application data. Pydantic's `model_rebuild()` instead resolves model types, including forward references; the similarly named operations have different purposes.

**ERD** — entity–relationship diagram: a view showing entity classes, their fields, and relationships. In Maxitor it is generated from the declared model, not obtained by inspecting database tables. A frame around specialization alternatives is a visual grouping, not an additional entity.

See [Relations between entities](../tutorials/step-21-relations.md#generalization-and-specialization) for the complete example and [the reference](intents-and-invariants.md#entity-specialization-the-build-rules) for current restrictions.

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

## Common errors

**ValidationFieldError** — a violation of an aspect's contract (no field, wrong type, broken constraint). **NamingSuffixError** — a name without the mandatory suffix. **CyclicDependencyError** — a cycle in the `@depends` graph. **MissingSummaryAspectError / MissingMetaError / MissingCheckRolesError** — a mandatory declaration is missing.

---

<table width="100%"><tr>
  <td align="left"></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"></td>
</tr></table>
