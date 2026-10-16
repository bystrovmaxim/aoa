# Feature Specification: One shared coordinator graph, declared once

**Feature Branch**: `feature/issue-213-shared-graph-resource`

**Created**: 2026-10-16

**Status**: Draft

**Input**: User description: "https://github.com/bystrovmaxim/aoa/issues/213 — Maxitor hands the loaded graph to routes as a per-call factory, though it is one app-scoped object: the declaration must say what it means."

## Clarifications

### Session 2026-10-16

- Decision carried over from the issue: **nothing under `packages/aoa-action-machine/` changes.** A ready resource already works as a value in `connections` today: the resolver returns it as it is, and the boundary never opens or closes it. The framework owes this feature no new capability.
- Decision carried over from the issue: **the shared object is created when the application is built, and it resolves the loaded graph on every read** rather than caching one — the load endpoint may replace the graph for everyone, and a cached reference would answer with a graph that is no longer the loaded one.
- Decision carried over from the issue: **the actions' `@connection(DuckDBGraphResource, key=...)` declarations are not touched.** The key stays, the declared type stays; only the value the routes are handed changes. Maxitor's graph metadata is read from those declarations.
- Decision carried over from the issue: **the holder lives beside the application, not in the domain**, because what it reads is FastAPI application state.
- Decision carried over from the issue: **the delegation to the graph is explicit and short** — the operations the diagram routes use, and nothing else. No attribute forwarding of any kind.
- Decision carried over from the issue: **`sidebar_data` is untouched, and one graph per process stays as it is.** A second load still overwrites the graph for every caller; that known limitation is [#214](https://github.com/bystrovmaxim/aoa/issues/214), which will re-point this same holder at a session-scoped source, and this feature is shaped so that only the source changes there.
- Decision carried over from the issue: **this lands first, before [#215](https://github.com/bystrovmaxim/aoa/issues/215)**, so that Maxitor is not among the declarations that must be migrated when a per-call resource gains a mandatory way to be closed. A shared object that owns no lifecycle has nothing to close.
- Decision taken while writing this specification: **an absent application slot and an empty one are the same answer.** The application fills its slot when it starts; a read that arrives before that must give the named "not loaded" failure, not an attribute error from the application object. The answer must not depend on how far startup has got.
- Q: When a diagram route is called before any graph is loaded, what should the caller actually receive? → A: **The caller's behaviour must not change.** No exception handler, no new status and no new response body are added; the client sees exactly what it sees today. What changes is the failure raised inside the application — the clear handle error the issue asks for, naming the situation, in place of today's type error about a factory's return value. That difference is visible to the tests that call the route and to whoever reads the log, and to nobody else.
- Q: How far must the connections guidance be reworded, so that it stops recommending the shape this feature removes? → A: **Not at all — issue #213 says nothing about changing `docs/tutorials/step-17-connections.md`.** The guidance is not part of this feature; User Story 3 and FR-015 are withdrawn below, and the observation is kept only so it is not rediscovered. Whether that chapter should be reworded is a separate decision, and this specification does not make it.

## User Scenarios & Testing *(mandatory)*

The readers of this feature are a developer reading Maxitor's route declarations, and — before the first load — whoever reads the failure the shared resource raises: a developer debugging the process, or a test that drives the connection.

### User Story 1 - The diagram routes share one graph, and their declaration says so (Priority: P1)

A developer opens the module that builds Maxitor's application and reads the six diagram route registrations. Each one says: this route reads the application's loaded coordinator graph. There is one such graph — the one built by the last successful load — and every route reads that one. The declaration states one shared object, because one shared object is what the application has.

**Why this priority**: the whole value of the feature is the truthfulness of the declaration, and it is also what makes the next change safe. Today the six routes declare a resource created per call, the factory ignores that and returns one shared slot, and the truth can only be reconstructed by reading the body of a lambda. A reader is misled, and any change that gives per-call resources a lifetime — [#215](https://github.com/bystrovmaxim/aoa/issues/215) — would have to discover Maxitor's exception by hand.

**Independent Test**: build the application, load a graph, call any two of the six diagram routes, and confirm both read one and the same graph object; then read the six registrations and confirm the value handed to them is a ready resource rather than something created per call.

**Acceptance Scenarios**:

1. **Given** a built application with a graph loaded, **When** two different diagram routes are called, **Then** both read the same graph object and both answer as they did before.
2. **Given** the same application, **When** the routes are called twice in a row, **Then** the object read on the second call is the one read on the first — the sharing is across requests, not only across routes.
3. **Given** two applications built in one process, **When** a graph is loaded in one of them, **Then** the other reports no graph loaded, and neither reads the other's graph.
4. **Given** an application whose graph is loaded a second time, **When** a diagram route is called afterwards, **Then** it reads the newly loaded graph.

---

### User Story 2 - Before the first load, the failure names the situation (Priority: P2)

Someone reaches a diagram endpoint before anything has been loaded — the page is opened first and the load request is still in flight. The failure raised inside the application for that request says that no graph is loaded and that the load endpoint has to be called first. It does not say that a factory returned `None`. Whoever reads that sentence is the person debugging the running process or the test that drives the connection: the HTTP caller sees the adapter's generic server error, before this change and after it alike (Clarifications).

**Why this priority**: it is the first thing that happens to every new deployment, and today the failure describes the framework's own plumbing instead of the situation — `PerCallConnection factory for key 'DuckDBGraph' must return BaseResource, got 'NoneType'`. Nothing in that sentence names what is wrong or what to do, and it is the same sentence whether the graph was never loaded or the load failed. The message is the only thing about this case a developer can act on, because the adapter answers **every** uncaught exception with one generic body and writes nothing to the log — so no caller and no log ever carries the text, and only a direct read of the resource does.

**Independent Test**: build the application, read the shared resource without loading anything, and confirm the named failure; then call each of the six diagram routes and confirm each answers exactly what it answered before this change.

**Acceptance Scenarios**:

1. **Given** a built application with nothing loaded, **When** the shared resource is read, **Then** the failure names the situation — no graph is loaded — and states that the load endpoint must be called first.
2. **Given** a read that arrives before the application has finished starting, **When** the slot for the graph does not exist yet, **Then** the answer is the same named failure, not an attribute error from the application object.
3. **Given** the same application after a successful load, **When** the resource is read, **Then** it answers normally and no failure is raised.
4. **Given** a load that failed, **When** the resource is read afterwards, **Then** the named failure is raised, and a graph loaded successfully earlier is still the one being read.

---

### User Story 3 - *(withdrawn)* The framework's guidance stops recommending this shape

A developer reads the connections chapter to decide how to declare a shared resource that only becomes available after the application has started — a store filled by a load request, a client created in the startup hook. The chapter answers: declare it as a ready resource, one object for the application, that resolves the value when it is read. It no longer says to keep the shared object in an external holder and read it from inside a factory that creates a resource per call.

**Why this was withdrawn, and where it went**: the observation is real and was confirmed in the repository — `docs/tutorials/step-17-connections.md` says today, in its "What to choose" section, that a resource becoming available only after startup "is kept in an external holder object and read from it inside `PerCallConnection.factory`", which is precisely the shape this feature deletes from Maxitor. But the maintainer settled it directly: **issue #213 does not touch that document.** Rewording the chapter is a separate decision with its own scope, and it is not smuggled into this feature. The story is kept here, and FR-015 and SC-012 with it, so the reasoning is not lost — a reader of this specification should still know why Maxitor looked the way it did.

**Independent Test**: *(not applicable — withdrawn)*.

**Acceptance Scenarios**: *(none — withdrawn)*.

---

### Edge Cases

- A read that arrives after the application is built but before its startup hook has run: the answer is the named "not loaded" failure, not an attribute error (Clarifications; FR-007).
- A load that fails — the remote service is unreachable, the payload is not a graph: the previously loaded graph, if there was one, stays what the routes read. A failed load never clears the slot and never leaves a half-built graph in it.
- Two loads in a row: the second graph is what every route reads afterwards. Nothing is merged, and no caller is told about the replacement — that limitation is [#214](https://github.com/bystrovmaxim/aoa/issues/214).
- A load landing while a diagram request is being served: the request reads either the graph from before the load or the graph from after it, never a mixture of the two, because the read is one lookup of one reference.
- A query already running against a graph that is then replaced: it finishes against the graph it started on.
- Nested action calls: the shared object reaches the inner action as itself, not as a copy and not wrapped, so an inner action and its caller read the same loaded graph.
- The same connection supplied by hand — as Maxitor's own load path does for the sidebar, and as many tests do — keeps working unchanged, because the actions' declarations do not change.
- A resource that is never read: building the application without loading anything must not fail, and must not build a graph.
- Two applications in one process (as the test suite has): each reads its own loaded graph and its own slot.
- The shared object has no lifecycle at all: nothing opens it before a run, and nothing closes it after, on success, on failure or on cancellation.

## Requirements *(mandatory)*

### Functional Requirements

**The declaration**

- **FR-001**: Every diagram route in Maxitor MUST declare its access to the coordinator graph as one ready resource — the same object for every route and every request — and MUST NOT declare it as something created per call.
- **FR-002**: That resource MUST be created while the application is being built, so that the declaration is complete before any route can be reached; it MUST NOT be created inside a request handler or on the first request.
- **FR-003**: The resource MUST be a value the framework accepts as a ready resource in a route's connections, so that the declaration and the framework's own check agree about what it is.
- **FR-004**: The resource MUST be bound to the application that created it. Two applications built in one process MUST NOT read each other's loaded graph, and loading a graph in one MUST leave the other reporting nothing loaded.

**Reading the loaded graph**

- **FR-005**: Reading the resource MUST resolve the graph loaded in its own application at the moment of the read, so that a graph loaded after the application was built, or loaded again later, is what the route sees. The resource MUST NOT keep a graph of its own from an earlier read.
- **FR-006**: The resource MUST expose the operations the diagram routes use — the connection handle, and the query that returns rows as dictionaries. It MUST NOT forward arbitrary attributes or calls to the graph it resolves.

**Failure before a graph exists**

- **FR-007**: Reading the resource when no graph is loaded MUST fail with the framework's own handle error, naming the situation: that no graph is loaded and that the load endpoint must be called first. A slot that does not exist yet MUST be reported exactly as an empty one, so that the answer does not depend on how far the application's startup has got.
- **FR-008**: That failure MUST NOT be a type error about the shape of the connection — specifically not today's message about a per-call factory having to return a resource — and MUST NOT name the framework's plumbing in place of the caller's situation. What a caller receives over HTTP MUST stay exactly as it is today: no exception handler is registered for this failure, no status is chosen for it, and no response body is shaped for it. The adapter's existing catch-all already answers every uncaught exception with one generic body and nothing in the log, so this requirement is met by adding nothing.

**Lifecycle**

- **FR-009**: The resource MUST own no lifecycle. It MUST NOT open, close, begin, commit or roll back anything, and it MUST be passed through as itself when it reaches a nested action, with no wrapper. A per-call resource's future obligation to be closed — [#215](https://github.com/bystrovmaxim/aoa/issues/215) — MUST NOT reach it.

**What stays as it is**

- **FR-010**: The connection key and the actions' `@connection` declarations MUST NOT change.
- **FR-011**: The load endpoint MUST stay the only writer of the loaded graph, and MUST keep writing it into one application-scoped slot, overwriting the previous graph for every caller. A load that fails MUST leave the slot as it was.
- **FR-012**: The sidebar data and its route MUST be untouched.
- **FR-013**: No file under `packages/aoa-action-machine/` may change.
- **FR-014**: For any loaded graph, the six diagram routes MUST answer exactly as they answer today.

**Documentation**

- **FR-015** *(withdrawn with User Story 3)*: an earlier version of this specification required the framework's own guidance to stop recommending that a shared resource which becomes available only after the application starts be declared as a resource created per call. **That requirement is withdrawn**: issue #213 does not touch `docs/tutorials/step-17-connections.md`, and rewording that chapter is a separate decision with its own scope. What this feature owes to documentation is what the constitution asks of every change — the module header and the docstrings of what it adds, and the changelog article for the work.

### Key Entities

- **Coordinator graph**: the in-memory, app-scoped object built from the loaded service's coordinator model, over which the diagram routes run their queries. There is one per application.
- **Shared graph resource**: the ready, app-scoped resource every diagram route is handed. It resolves the application's currently loaded graph on each read and holds none of its own.
- **Application slot**: the single place a loaded graph is written to and read from for the whole application. Writing it replaces the graph for every route.
- **Load endpoint**: the request that builds the graph from a service URL and writes it into the slot. It is the only writer, and it loads the sidebar from the same freshly built graph.
- **Diagram route**: one of the six endpoints that answer a diagram or a list drawn from the loaded graph.
- **Per-call declaration**: the shape being removed — a declaration that says a resource is created for each call while the value handed over is one shared object.

### Out of scope

- **Several graphs in one process.** Sessions, per-user state and isolation are [#214](https://github.com/bystrovmaxim/aoa/issues/214); this feature keeps the single slot and only changes how it is declared.
- **A lifetime for resources created per call.** A mandatory way to close such a resource is [#215](https://github.com/bystrovmaxim/aoa/issues/215); this feature simply takes Maxitor out of that migration.
- **Authentication and authorization.** Nothing here decides who may load or read a graph.
- **The shape of the graph or the queries over it.** The routes keep answering from the same data as before.
- **Any new capability in `aoa-action-machine`.** The framework is expected to need no change at all (Clarifications).
- **The HTTP answer for an unloaded viewer, and any user-visible state for it.** The caller's behaviour is deliberately unchanged (Clarifications); making the failure legible over HTTP, or showing it in the viewer, is a change of its own and is not made here.
- **Making the failure visible at all.** The adapter's catch-all middleware turns every uncaught exception into one generic server error and writes nothing to the log, so the clearer message is read only where the connection is driven directly. Logging it, or answering with a deliberate status, is a decision about the adapter and is not made here.
- **Rewording the connections guidance.** `docs/tutorials/step-17-connections.md` is not part of this feature (User Story 3, withdrawn).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With a graph loaded, all six diagram routes return exactly what they return today — measured by running the existing route-level checks with no edit to their expectations.
- **SC-002**: The value declared on each of the six routes is a ready resource: the framework's own check accepts it as one, and it is created once while the application is being built rather than per request.
- **SC-003**: Across two consecutive requests to any two of the six routes, the graph object read is one and the same — measured by identity, not by equal content.
- **SC-004**: Two applications built in one process report distinct shared resources; after a graph is loaded in one, the other still answers every diagram route with the named "not loaded" failure.
- **SC-005**: After the graph is loaded a second time, 100% of the six routes read the newly loaded graph and 0% keep reading the previous one.
- **SC-006**: With nothing loaded, reading the shared resource raises the named "not loaded" failure in 100% of cases and raises a type error about a per-call factory's return value in 0%; the same holds for a read arriving before the application's startup hook has run. The response a caller receives over HTTP is unchanged from today in status and in body — the adapter's generic server error for the routes that reach the connection, its usual validation answer for the two that require a parameter.
- **SC-007**: A load that fails changes nothing — every diagram route still reads the graph loaded before it, or, if none was loaded, answers with the named failure.
- **SC-008**: The shared resource offers only the operations the diagram routes use; an attribute the loaded graph has but the routes do not use is not reachable through it.
- **SC-009**: The shared resource offers nothing to open and nothing to close — no operation of that kind exists on it — so a successful run, a failed run and a cancelled run are alike in touching no lifecycle, and a nested action reaches the same object rather than a copy.
- **SC-010**: The change touches zero files under `packages/aoa-action-machine/`, zero `@connection` declarations in Maxitor's actions, and nothing in the sidebar route or its data.
- **SC-011**: The whole existing Maxitor test suite passes with no test edited except the ones this feature adds.
- **SC-012** *(withdrawn with User Story 3)*: an earlier version required that the connections guidance contain no recommendation to declare a shared, late-arriving resource as a resource created per call. **Withdrawn**: the guidance is outside this feature, and a check against a document this change does not touch would assert nothing about this change.

## Assumptions

- One graph per process is deliberate and stays. A second load overwriting the graph for everyone is a known limitation owned by [#214](https://github.com/bystrovmaxim/aoa/issues/214), not a defect this feature introduces or fixes.
- The framework already accepts a ready resource in a route's connections and never opens or closes it, so this feature needs nothing from `aoa-action-machine`. The design is not a workaround: it is the mode the object always belonged to.
- The resource resolves per read and keeps no reference to a graph of its own, because the loaded graph can be replaced at any time and a stale reference would answer from a graph that is no longer the loaded one.
- The holder belongs to the API layer, beside the application, because what it reads is the application's own state; the domain layer stays unaware of it.
- The diagram actions keep reaching the graph through their declared connection key and the type they declare it with. Neither the key nor the declared type changes, so Maxitor's published graph metadata is unaffected.
- The holder's shape — one resource, resolving on read — is chosen to survive [#214](https://github.com/bystrovmaxim/aoa/issues/214), where only the source it resolves from becomes session-scoped.
- A read of the application slot is a single reference lookup, so it either sees the graph from before a load or the one from after it; no locking is introduced and none is needed for a local viewer.
- The connection key used by the six routes and the one the load path uses for the sidebar are the same key, and that stays true.
- The project constitution applies: English in commits, in git and in code; module headers; AI-CORE blocks on public classes; one-line docstrings; documentation written with the change; a Russian draft beside each page the maintainer reads; and the check run taken to zero as the last step of the work.
