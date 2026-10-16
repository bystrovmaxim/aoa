# Phase 0 — Research: One shared coordinator graph, declared once

**Feature**: `specs/005-shared-graph-resource` · **Date**: 2026-10-16

Every decision below was made against the code in this repository, not against the issue's
sketch. Where the sketch and the code disagree, the code won and the deviation is named.

---

## R1. Does a ready resource satisfy the actions' `@connection(DuckDBGraphResource, key=…)`?

**Decision**: Yes. The declaration on the action fixes a **key**, and the framework checks the
supplied value only for being a `BaseResource`. The holder can therefore be supplied under the
`DuckDBGraph` key while the action keeps declaring `DuckDBGraphResource`, and no action changes.

**Rationale**: `ConnectionValidator._validate_connection_value_types`
(`packages/aoa-action-machine/src/aoa/action_machine/runtime/connection_validator.py:104-114`)
loops over the supplied values and returns an error for exactly one condition —
`not isinstance(value, BaseResource)`. It never compares the value with the type the action
declared. The declared type is read by `ActionGraphNode.connection_keys()` only to extract
**keys**, and by the graph builder to publish metadata.

**This is the single riskiest assumption in the feature**, because every other part of the plan
depends on it and a wrong reading would force a change under `packages/aoa-action-machine/`,
which FR-013 forbids. It is therefore not left to inspection: the route-level tests call all six
routes with the holder and assert they answer exactly as before.

**Alternatives considered**:
- *Make the holder a `DuckDBGraphResource` subclass* — rejected: it would have to be built by
  `build_from_json`, which needs the graph, which does not exist at app-build time. Inheriting the
  type without the data is a lie of the same kind the feature removes.
- *Change the actions' `@connection` to declare a new holder type* — rejected: FR-010 forbids it,
  and the declared type is Maxitor's published graph metadata.

---

## R2. What does the holder subclass?

**Decision**: `BaseResource` directly, with `@meta(description=…, domain=DiagramsDomain)`.

**Rationale**: `ExternalServiceResource.__init__` takes the service and stores it
(`external_service_resource.py:59-61`). The holder has no service at construction — the graph is
loaded later — so subclassing it would mean constructing with a placeholder and overwriting it on
each read. That is a mutable fake, and the feature exists to remove a declaration that pretends.
`BaseResource` requires only `get_wrapper_class()` and the rollup answer, both trivial here.

`@meta` is required by convention: `BaseResource`'s own module docstring says every resource
manager declares it. It is **not enforced** for this class — `BaseResource` is
`@exclude_graph_model` (`base_resource.py:71`), so the holder never becomes a `ResourceGraphNode`
and `MissingMetaError` cannot reach it. Declared anyway, because a rule the framework states and
this code would silently skip is not a rule.

**Alternatives considered**:
- *`ExternalServiceResource[duckdb.DuckDBPyConnection]` with a lazily-set service* — rejected
  above.
- *No `@meta` at all, since it is unenforced* — rejected: it would put a second exception into the
  codebase beside Maxitor's existing one, which is exactly the debt this feature is paying down.

---

## R3. How is the application slot read, so that an absent slot and an empty one behave alike?

**Decision**: `getattr(self._app.state, "duckdb_graph", None)`, and `None` raises the named error.

**Rationale**: the issue's sketch reads `self._app.state.duckdb_graph` directly. That attribute is
created in the lifespan (`app.py:67`), so a read that arrives **before the lifespan has run**
raises `AttributeError` from the application object — the same class of failure the feature
removes, merely spelled differently. The maintainer settled this in clarification: a slot that does
not exist yet must be reported exactly as an empty one, so the answer does not depend on how far
startup has got. `getattr` with a `None` default is that decision in one expression.

**Alternatives considered**:
- *Direct attribute access, as the issue sketched* — rejected in clarification (above).
- *Initialise the slot at app-build time instead of in the lifespan* — rejected: it moves a line of
  `app.py` that no requirement asks to move, and it would still leave `None` to be handled.

---

## R4. What does the holder answer when asked about rollup, and what wrapper class does it declare?

**Decision**: `check_rollup_support()` returns `False`; `get_wrapper_class()` returns `None`.

**Rationale**: nothing in `packages/aoa-maxitor` mentions rollup at all (measured — zero matches
for `rollup` under `packages/aoa-maxitor/src`), so the answer is never consulted today; `False` is
the honest answer for an in-memory read-only store and it matches `ExternalServiceResource`'s own
answer, so the holder is indistinguishable from the resource it replaces.

`None` is the point of the feature: `ToolsBox._wrap_connections` (`tools_box.py:191`) calls
`get_wrapper_class()` when propagating connections to child actions, and a `None` result passes the
object through unchanged. The holder has no lifecycle to protect, so a wrapper would be pure
ceremony — and `WrapperExternalServiceResource` would be worse than ceremony: it delegates
`service` and `check_rollup_support` **only**, so wrapping the holder would silently drop
`execute_fetch_dicts` for any nested action. There are no nested readers of this connection today,
which is exactly why the mistake would not be noticed.

**Alternatives considered**:
- *Delegate to `ExternalServiceResource.get_wrapper_class()`* — rejected: it loses
  `execute_fetch_dicts` at nesting depth, as shown above.
- *Omit `check_rollup_support` and inherit the base, which raises `RollupNotSupportedError`* —
  rejected: it would make the holder answer *differently* from the resource it replaces, for a
  question nobody asks today.

---

## R5. How does the feature prove identity across requests without adding public surface?

**Decision**: identity is asserted **on the holder directly** — set `app.state.duckdb_graph` to a
recording stand-in, read `.service` twice, assert the same object comes back — and the six routes
are asserted **end to end** through the app (their JSON, the unloaded failure, a reload). The two
together are the acceptance; the holder is deliberately **not** published on `app.state` to make
the route-level read observable.

**Rationale**: the holder is created inside `create_app()` and captured in the route registrations'
closures, so a test cannot reach it from the app object. Exposing it (`app.state.duckdb_graph_holder`)
would be new public surface that no functional requirement asks for, added solely to be inspected.
The decomposition is sound because the six routes are declared with **one and the same value**
(FR-001): route-level identity follows from holder-level identity plus there being exactly one
value, and that "exactly one" is proved on its own — [R10](#r10-how-is-one-object-declared-once-proved-when-no-registration-is-reachable) records how, and why the obvious way of proving it does not work at all.

**Alternatives considered**:
- *Publish the holder on `app.state` for the test* — rejected above: test-driven public surface.
- *Monkeypatch `FastApiAdapter.get` to capture the `connections` argument* — rejected: it asserts
  against a mock's memory of a call instead of against the object the routes actually use, and it
  is brittle to an adapter refactor.
- *Read the registrations back after `create_app()`* — not rejected on taste but found **impossible**:
  see R10.

---

## R6. How is "the boundary never opens or closes it" checked, given `BaseResource` has no lifecycle?

**Decision**: assert that the holder **has none of the lifecycle members at all**
(`open`, `close`, `begin`, `commit`, `rollback`) and that `get_wrapper_class()` is `None`; assert a
successful request through a route completes without any lifecycle call being possible.

**Rationale**: `BaseResource`'s contract does not include `open`/`close` — they belong to
`BaseController`/`SqlResource` — so "zero opens recorded" cannot be measured by instrumentation on
an object that has no `open` to call. The measurable statement is the stronger one: the members do
not exist, and no wrapper will be constructed for it. SC-009 is satisfied by absence plus the
passthrough assertion, not by a counter that would always read zero.

**Alternatives considered**:
- *Instrument a stand-in resource that records lifecycle calls* — rejected as theatre: it would
  verify the test double, not the holder.

---

## R7. How are the routes tested at all, when no Maxitor test has ever built the app?

**Decision**: a new test module that calls `create_app()` and drives it with
`fastapi.testclient.TestClient`. `httpx` is already a dependency of `aoa-maxitor`
(`pyproject.toml`), so `TestClient` works with no addition. Two modes are used deliberately:
default `raise_server_exceptions=True` to assert the **`HandleError` message** for the unloaded
case, and `raise_server_exceptions=False` to assert the **unchanged HTTP answer** the caller gets.

**Rationale**: the acceptance partly concerns *declarations on routes*, which only exists once an
app is built. The `raise_server_exceptions` split is what makes the maintainer's clarification
testable rather than merely written down: the raised failure changes, the HTTP response does not.

**Alternatives considered**:
- *Test only the holder, never a route* — rejected: it cannot catch a route registered with the
  wrong connection value, which is precisely the bug this feature fixes.
- *Test the six actions directly with a real `DuckDBGraphResource`, as every existing test does* —
  rejected for the same reason; those tests stay green either way, which is why the bug survived.

---

## R8. Where is the clearer failure actually readable?

**Decision**: the acceptance is written against a **direct read of the shared resource** (and, for
the routes, against the response they return). It is explicitly **not** written as "the route raises
`HandleError`", because no route can: the adapter swallows it before any caller or log sees it.

**Rationale — measured, not read.** A throwaway proof built the adapter exactly as `create_app()`
does and drove it with `TestClient`. Three results:

1. `TestClient(raise_server_exceptions=True)` — **no exception escaped to the test**. Neither today's
   `TypeError` nor the new `HandleError` reaches a caller, because `_CatchAllErrorsMiddleware`
   (`packages/aoa-fastapi-adapter/src/aoa/fastapi/adapter.py:527-550`) wraps every request in
   `try/except Exception` and returns `JSONResponse(500, {"detail": "Internal server error"})` —
   **without logging the exception it catches**.
2. The baseline `create_app()` answers all six routes without a graph loaded as the table below
   shows. Four reach the connection and get the generic 500; two require a query parameter and are
   rejected with `422` before the connection is touched at all.

   | Route | Today, nothing loaded |
   | --- | --- |
   | `/api/v1/list-domains` | `500 {"detail":"Internal server error"}` |
   | `/api/v1/list-entities` | `500 {"detail":"Internal server error"}` |
   | `/api/v1/list-node-types` | `500 {"detail":"Internal server error"}` |
   | `/api/v1/full-graph` | `500 {"detail":"Internal server error"}` |
   | `/api/v1/lifecycle-finite-automaton` | `422` — a required query parameter is missing |
   | `/api/v1/domain-use-case-diagram` | `422` — a required query parameter is missing |

3. With the holder in place, the same four routes still answer `500 {"detail":"Internal server
   error"}`, the two still answer `422`, and a direct read of the resource raises
   `HandleError("Graph is not loaded: call POST /api/load first.")`. With a graph loaded, two routes
   answered `200` with their usual payloads, the same graph object was read by both, and a reload
   was observed by the next read.

**Consequences carried into the artefacts**:

- The maintainer's clarification ("the caller's behaviour must not change") is not merely honoured —
  it is what the framework already does, and doing nothing is the correct implementation of it.
- The spec's User Story 2 no longer claims an operator reads the message in a log; nothing is logged.
  The clearer message is read where the connection is driven directly: a test, a debugger, or a
  script that runs the machine. Making it visible over HTTP or in a log is named in the spec's
  Out of scope as a decision about the adapter.
- The route-level test asserts the **response** (500 / 422, unchanged), and the failure is asserted
  on the resource. Asserting `HandleError` through `TestClient` would be a test that can never fail
  for the right reason.

**Alternatives considered**:
- *Assert the message through `TestClient` with `raise_server_exceptions=True`* — rejected: measured
  above to be impossible; the middleware catches first.
- *Add logging or an exception handler so the message surfaces* — rejected for this feature: it is a
  change in the adapter's behaviour, contradicts the maintainer's decision, and is out of scope.
  Recorded as a follow-up question instead.

---

## R9. Where does the changelog article go?

**Decision**: **one** article in `packages/aoa-maxitor/CHANGELOG.md` under `[Unreleased]`. The
`docs/CHANGELOG.md` line is added only if the maintainer judges this work framework-level, and that
is asked at the task rather than assumed.

**Rationale**: `packages/aoa-maxitor/CHANGELOG.md` was updated by the most recent Maxitor-facing
change (#199, commit `22760574`) and already carries an `## [Unreleased]` section;
`docs/CHANGELOG.md` was last written for a framework-level change (#196). Principle VI names
`docs/CHANGELOG.md`, so the difference is recorded in the plan's Constitution Check instead of
being resolved silently.

**Alternatives considered**:
- *Write both* — rejected: Principle VI asks for one article, and two copies of one article drift.

---

## R10. How is "one object, declared once" proved, when no registration is reachable?

**The obvious answer does not work, and this was measured.** The first draft of the task said a test
would "read `create_app()`'s registrations". It cannot:

- `FastApiAdapter.build()` creates a **fresh** `FastAPI` and registers one endpoint per record with
  `app.add_api_route(..., endpoint=_make_endpoint(record, …))`
  (`packages/aoa-fastapi-adapter/src/aoa/fastapi/adapter.py:802-850`). The endpoint is a **closure**
  over `record`, and `record.connections` is what holds the declared value.
- The records live on the adapter (`BaseAdapter._routes`), and `create_app()` builds the adapter
  inline, chains six `.get(…)` calls and passes the result to `fastapi_app.mount(...)` — so the
  adapter object is discarded and nothing points at it afterwards.
- `app.state` carries only `machine`, `duckdb_graph` and `sidebar_data`, all set in the lifespan.
  The mounted sub-application exposes `APIRoute` objects whose `endpoint` is that closure, and
  nothing else.

So there is no supported way to read back which value a route was declared with.

**Decision**: prove "one object" by **counting real constructions**, and prove the sharing
separately, then take the two together.

1. **Exactly one per application.** Wrap `DuckDBGraphHolder` in the `aoa.maxitor.api.app` module
   namespace with a spy that records real instantiations, call the **real** `create_app()`, and
   assert exactly one instance was built. Because the spy wraps the real class rather than
   replacing it, the application under test is the real one; what is observed is a real
   construction, not a mock's memory of a call. Two `create_app()` calls must produce two
   different instances (FR-004).
2. **Every route reads the shared slot.** Point `app.state.duckdb_graph` at a recording stand-in and
   confirm all six routes reach it (and, in the reload case, that all six observe the replacement).

Together: exactly one holder exists, and all six routes read the one slot through a holder — so all
six use that one holder. Neither half alone is enough, which is why both are asserted.

**Alternatives considered**:
- *Reach into `endpoint.__closure__` and pull `record.connections` out* — rejected: it depends on the
  adapter's internal closure layout, an implementation detail nobody promised to keep, so the test
  would break on a refactor that changes no behaviour.
- *Publish the holder on `app.state`* — rejected: new public surface no requirement asks for, added
  only so a test can look at it (R5).
- *Rebuild the adapter inside the test, mirroring `app.py`* — rejected: it would assert the test's
  own wiring, and would stay green if `app.py` were reverted to the per-call factory. That is
  precisely the regression this feature exists to prevent.

---

## R11. Does a ready resource change what a caller sees when nothing is loaded?

**It changes exactly one answer, and the two decisions behind this feature cannot both hold.**

**Measured.** Built the unmodified `app.py` from `HEAD` and the new one side by side, drove all six
routes with the lifespan running and nothing loaded:

| Route | Before | After |
| --- | --- | --- |
| `/api/v1/list-domains` | `500 {"detail":"Internal server error"}` | unchanged |
| `/api/v1/list-entities` | `500 {"detail":"Internal server error"}` | **`200 {"domain_slices":[]}`** |
| `/api/v1/list-node-types` | `500 {"detail":"Internal server error"}` | unchanged |
| `/api/v1/full-graph` | `500 {"detail":"Internal server error"}` | unchanged |
| `/api/v1/lifecycle-finite-automaton` | `422`, missing query parameter | unchanged |
| `/api/v1/domain-use-case-diagram` | `422`, missing query parameter | unchanged |

**Why.** `resolve_connections` used to call the factory **eagerly** and demand a `BaseResource`
back; with nothing loaded the factory returned `None` and every route failed before its action ran.
A ready resource always resolves, so the refusal now happens at the **first read** instead. That is
not a detail of this implementation — it is what "mode 1" means. Measured with a counting stand-in:
`/api/v1/list-entities` with no `domain_qualnames` never reads the connection at all (it short-circuits
to an empty result), while the same route **with** a filter reads it and fails as before.

**The conflict, stated plainly.** The issue asks the declaration to say what it means — one shared
object, mode 1. The clarification asks the caller's behaviour not to change. Those two cannot both
hold here, because the eager failure was a property of the factory being called at resolution time,
not of the object it returned. Every honest mode-1 design moves the failure to first read.

**Options, for the maintainer:**

1. **Accept the one difference.** A route that never reads the graph now answers its genuine empty
   result instead of a server error; the other five are byte-identical. Requires amending FR-008,
   SC-006 and `contracts/routes.md` R-3.3, and the caller-facing table in the quickstart.
2. **Preserve the caller's behaviour exactly.** Keep `PerCallConnection`, but give its factory the
   clear failure instead of returning `None`:
   `PerCallConnection(factory=lambda: holder_or_raise())`. Resolution then fails eagerly again and
   all six answers are unchanged. The cost is the one the issue exists to remove: the declaration
   still claims a fresh resource per call, and Maxitor stays inside #215's migration.

**What is in the code now**: option 1's behaviour, pinned so it cannot change unnoticed. The test
`test_routes_without_a_graph_divergence_for_list_entities` is a **strict `xfail`** carrying the other
five routes' recorded baseline; the moment the behaviour is restored it turns into an unexpected
pass and fails loudly. Nothing was decided by writing it down.

---

## R12. What is explicitly *not* researched, and why

- **Rewording `docs/tutorials/step-17-connections.md`.** Withdrawn in clarification: issue #213 does
  not touch it. The observation is preserved in the spec's withdrawn User Story 3 so it is not
  rediscovered from scratch.
- **Session-scoped state (#214) and a mandatory `finalize` for per-call resources (#215).** Both are
  separate issues. The holder's shape — one resource, resolving on each read — is chosen so that
  #214 changes only the source it resolves from, and so that #215 never reaches it.
- **Any change under `packages/aoa-action-machine/`.** Forbidden by FR-013 and unnecessary by R1.
