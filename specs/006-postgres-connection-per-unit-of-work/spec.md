# Feature Specification: One connection per unit of work, and one pool for the process

**Feature Branch**: `feature/issue-215-postgres-connection-per-unit-of-work`

**Created**: 2026-10-16

**Status**: Draft

**Input**: User description: "https://github.com/bystrovmaxim/aoa/issues/215 — `PostgresResource` opens **one** connection for the whole process and shares it between every method of the subclass: parallel calls fail with `InterfaceError`, transactions interleave and one `COMMIT` commits another's rows. A pool in the lifespan and a connection per unit of work are needed."

## Clarifications

### Session 2026-10-16

- Decision carried over from the issue: **the resource equals one unit of work.** The pool may be shared; a resource holding a connection may not. A resource takes its connection in `open()` and gives it back in `close()`; it is never shared between two concurrent callers.
- Decision carried over from the issue: **the connection is taken in `open()`, not in the constructor**, because the constructor is synchronous. The shape is `LedgerResource({"dsn": ...})` for its own connection or `LedgerResource(pool=pool)` for one borrowed from a ready pool — **exactly one of the two**, and both or neither is a construction error. `pool` is a keyword parameter.
- Decision carried over from the issue: **the pool is created once by the application, in the lifespan, and closed there**, from the same connection parameters. Size and timeout belong to the pool: `create_pool` defaults to `min_size=10, max_size=10, timeout=None` — "ten at once" and "wait forever" — and both are set explicitly.
- Decision carried over from the issue: **the defect is fixed even without a pool.** One connection per unit of work is the correctness fix; the pool adds economy, not correctness.
- Decision carried over from the issue: **`PerCallConnection` gains a mandatory `finalize`.** `PerCallConnection(factory, finalize)`; the finalizer may be synchronous or asynchronous, because returning a connection to a pool is asynchronous. Being mandatory is the point: a resource created per call cannot be declared without saying how it is closed.
- Decision carried over from the issue: **the boundary — the adapter — owns the per-call lifecycle.** Resources with a lifecycle are opened before the run; after the run `finalize(resource)` is always called, in a `finally`, on success, on exception and on cancellation. A closing error must not mask the original error of the run.
- Decision carried over from the issue: **the pool is not put into `connections`** — the action does not use it. It is process state and reaches the route through a holder, the pattern already described in step 17 for "a resource that becomes available after the app starts".
- Decision carried over from the issue: **the resource never closes the pool.** Closing a borrowed connection returns it to the pool; it does not close the pool.
- Decision carried over from the issue: **the public generic query surface is not touched here.** Removing the public `execute()` from the SQL contract and moving the query surface to protected driver helpers is [#216](https://github.com/bystrovmaxim/aoa/issues/216). This feature adds no new public query method.
- Decision carried over from the issue: **`close()` enters the contract as a concrete no-op default** on both `ProtocolSqlResource` and `SqlResource`, so the eight demo stubs and the test subclasses need no edits; only the driver implements it for real.
- Decision carried over from the issue: **the wrapper forbids more than it does today.** A nested action must not close someone else's connection: `close`, `__aenter__` and `__aexit__` join `open`/`begin`/`commit`/`rollback` as forbidden, and `acquire` stays unexposed. `isinstance(wrapper, ProtocolSqlResource)` must stay true.
- Decision carried over from the issue: **Maxitor is not migrated here.** It moved to mode 1 in [#213](https://github.com/bystrovmaxim/aoa/issues/213) (closed); the nested-action wrapper and the choice of mode are what the documentation must state.
- Decision taken while writing this specification: **the specification uses the library's own public vocabulary** — "resource", "connection", "pool", "unit of work", "boundary", "factory", "finalize" — because this feature *is* that vocabulary. It is not written in end-user terms, and the API shapes above are requirements rather than choices left to planning. `[NEEDS CLARIFICATION]` markers are therefore used only where the issue leaves a decision genuinely open.
- Decision taken while writing this specification: **the three open points below were resolved as follows.** (1) The changelog article goes under `## [Unreleased]` in both packages, with no dated heading and no version bump: a version in `pyproject.toml` names the version under development, and cutting the release — the dated heading — is the maintainer's act, not this feature's (corrected by the maintainer after the first draft of this specification read the metadata version as a release). (2) The demo stays runnable with **no PostgreSQL**: the pool is created only when a DSN is given, and every test runs against a connection stub. (3) The boundary hook goes into **both** adapters, at the four places where connections are resolved before the run today (three in the FastAPI adapter, one in the MCP adapter).
- Decision taken while writing this specification: **the requirements the issue states implicitly are written down as requirements, not left to planning.** Reading the holder before it is filled must give a named failure rather than an attribute error; an exhausted pool must end in a named failure rather than an unbounded wait; the resources already opened must still be finalized when a later opening of the same call fails; and a resource built without a pool must not reach any pool. Each of these follows from an invariant the issue states, and each is what makes the corresponding check writable.
- Decision taken while writing this specification: **the construction error is raised when the resource is constructed, and only there.** A per-call factory constructs its resource while the call is running, so "both descriptions, or neither" is caught at the first construction — the constructor is synchronous, and a factory that cannot construct its resource fails the call. Validating a declaration's callables, by contrast, happens when the declaration is validated, without calling the factory.
- Decision taken while writing this specification: **the "several pools in one process" edge and the out-of-scope bullet are not in conflict.** What is out of scope is a *design* for several pools coexisting per application or per session; what the tests assert is that two independent applications in one process do not reach each other's pool — the ordinary isolation the existing suite already relies on when it builds two applications.

### Session 2026-10-16 — clarification

- Q: Where should the application hang its own pool creation and closing, given that the adapter's builder does not accept a startup hook today? → A: **A general lifecycle option on the adapter's builder** — `build(lifespan=...)` taking one asynchronous context manager, inside which the application creates and closes **its own** pool. The framework does not create or configure the pool, and nothing database-specific enters the adapter; the option serves a pool, an HTTP client or a Redis client alike.
- Q: Where should the substitution point be, so that tests of the resource and the pool run without PostgreSQL? → A: **Tests supply a fake pool and a fake connection through `pool=`**, and the resource's own connection creation is left to the demo and the examples rather than to a unit test. The public constructor stays exactly the shape the issue states — `(connection_params=None, *, pool=None, rollup=False)` — and grows no substitution parameter.
- Q: What should the framework do when a per-call factory returns one and the same shared resource on every call, as Maxitor did before [#213](https://github.com/bystrovmaxim/aoa/issues/213)? → A: **Nothing — the framework neither forbids nor detects it, and the finalizer still runs exactly once per call.** Policing the factory would need either a marker on the resource or a comparison across calls: a new concept and a new branch in the boundary for a case that the application already gets right by declaring a ready resource. The rule is documented instead: the finalizer closes the resource of *this* call, so a declaration whose factory returns a shared object owes a finalizer that is harmless there.
- Q: Which domain should the demo use to show the pattern of a pool with a per-call resource? → A: **The existing `identity` domain is extended** with a Postgres resource that has a read method and a transactional method, rather than adding a new domain.
- Q: Which explicit pool bounds and timeout should the examples and the demo carry as the pattern to copy? → A: **the values the issue states — `min_size=1, max_size=10` stated where the pool is created, and `30` stated as the wait bound where the wait happens** — so that the requirement to state them explicitly is visible in the code a reader copies.
- Q: What must closing do when a transaction is still open at that moment? → A: **It raises, and that raise is the error the caller gets.** Fail-fast is the principle: code that opened a transaction commits it or rolls it back, and a framework that quietly repairs the omission lets the omission drift. The resource tracks the transaction (`begin` opens it, `commit`/`rollback` close it), and a close that finds it open issues `ROLLBACK` itself — never leaning on the driver's own reset — returns the connection, and raises `TransactionLeftOpenError`. That error is a **contract violation by the caller's code**, not an operational closing failure: it is the raised error even when the run had already failed, with the run's error chained as its cause; it is never demoted to a note, and it is not a failure to catch and continue past. The connection is returned **before** the raise, so fail-fast costs no connection. A second close finds an empty resource and stays silent (FR-006). The one exception is cancellation: a cancelled task's `CancelledError` still propagates and the violation is recorded beside it, because replacing a cancellation with another error breaks cancellation itself.

## User Scenarios & Testing *(mandatory)*

The readers of this feature are a developer running concurrent requests against a Postgres-backed action, a developer reading a route declaration that creates a resource per call, and a library user reading the SQL resource contract.

### User Story 1 - Concurrent requests each get their own connection, and transactions stay apart (Priority: P1)

Two requests arrive at the same time. Each is served by its own resource, each resource holds its own connection for the length of its unit of work, and neither sees the other. Each transaction starts and ends on the one connection its owner holds: a coroutine that yields between `BEGIN` and `COMMIT` does not let anyone else's statement run on its session, and one operation's `COMMIT` never commits another's rows.

**Why this priority**: this is the defect. Sharing one connection per process makes parallel calls fail intermittently with a "another operation is in progress" interface error, and, worse, interleaves transactions so that one caller's commit lands another caller's data. That is data corruption, and everything else in this feature exists to make the fix economical rather than to make it correct.

**Independent Test**: run many concurrent units of work against one resource declaration and confirm none fails with the shared-connection error and no transaction's rows are committed by another's commit; then confirm the same with a pool-backed resource and a shared pool.

**Acceptance Scenarios**:

1. **Given** a resource backed by the library's connection harness, **When** 30 requests are served concurrently, **Then** every one succeeds and none fails with a "another operation is in progress" error.
2. **Given** two concurrent units of work, **When** each runs its own `BEGIN` … `COMMIT`, **Then** no statement of one runs inside the other's transaction and each commits exactly its own rows.
3. **Given** a unit of work that raises, **When** it ends, **Then** its connection does not stay held and a later unit of work can take one.
4. **Given** a unit of work that is cancelled, **When** it ends, **Then** its resource is closed exactly as on success.

---

### User Story 2 - The application keeps one pool for its lifetime, with explicit size and timeout (Priority: P2)

An application starts, builds one pool from its connection parameters, and serves requests from it; when the application stops, the pool is closed. The pool's bounds are stated rather than inherited from the library's defaults, so the process holds a known number of connections and a request that arrives when the pool is exhausted waits a bounded time instead of forever.

**Why this priority**: opening a connection per request is correct but expensive, and a process that opens as many as it is asked for will exhaust the database's own budget. The pool is what turns the correctness fix into something an application can run in production — but the fix is already complete without it, so it ranks below the defect.

**Independent Test**: start an application with a pool, serve concurrent requests through a pool-backed resource, stop the application, and confirm the pool is created once, its configured ceiling is never exceeded, and it is closed on shutdown.

**Acceptance Scenarios**:

1. **Given** an application starting with a pool, **When** it starts, **Then** exactly one pool is created, from the same connection parameters the resource would use, and the pool's size bounds and timeout are the ones the application set rather than the library defaults.
2. **Given** a pool with a ceiling of 2 and 3 concurrent requests, **When** all three are issued, **Then** at most 2 connections are held at once and the third completes after the others release theirs.
3. **Given** a pool that stays exhausted longer than its timeout, **When** a request waits for a connection, **Then** the wait ends in a named failure rather than hanging.
4. **Given** a running application, **When** it shuts down, **Then** the pool is closed once and the holder no longer offers it.
5. **Given** a resource that borrowed a connection from a pool, **When** the resource is closed, **Then** the connection returns to the pool and the pool stays open.

---

### User Story 3 - A resource created per call cannot be declared without saying how it is closed (Priority: P3)

A developer writes a route that needs a resource for the duration of one call — a connection from a pool. The declaration refuses to be written half-way: alongside the factory that creates the resource, it must name the finalizer that closes it and returns the connection. The boundary then runs the pair — create, open, run, finalize — on every path out of the run.

**Why this priority**: without this, a per-call resource over a pool either leaks connections or leaves the developer to close them by hand outside the framework, which is the same gap that makes today's `_conn` reachable from outside. It ranks below correctness and economy because it is the mechanism those two rely on, not an outcome of its own.

**Independent Test**: declare a per-call resource with a factory and a finalizer, run a route on a successful path, on a failing path and under cancellation, and confirm the finalizer ran exactly once in each case and the original failure was not masked.

**Acceptance Scenarios**:

1. **Given** a declaration with both a factory and a finalizer, **When** the route runs successfully, **Then** the finalizer is called exactly once and after the run.
2. **Given** the same declaration, **When** the run raises, **Then** the finalizer is called exactly once and the run's own error reaches the caller unchanged.
3. **Given** the same declaration, **When** the run is cancelled, **Then** the finalizer is called exactly once.
4. **Given** a declaration with no finalizer, **When** the route record is built, **Then** it is rejected as incomplete.
5. **Given** a resource without a lifecycle, **When** it is declared per call with a finalizer, **Then** the run is opened by nobody and the finalizer is still called once.
6. **Given** a finalizer that raises on an otherwise successful run, **When** the route returns, **Then** the closing failure surfaces rather than being silently dropped.

---

### User Story 4 - A held connection can be closed from outside, and a nested action cannot close it (Priority: P4)

A developer reads the SQL resource contract to learn what a resource is obliged to offer, and finds closing among the obligations: every SQL resource answers `close`, the driver really releases its connection, and a resource that holds none answers harmlessly — so eight existing demo stubs and the test subclasses need no edits. A nested action, which is handed a proxy, cannot close the connection it does not own.

**Why this priority**: it removes the last reason to reach through the private connection from outside, and it closes the one hole the wrapper still has — a nested call able to tear down its caller's connection. It ranks last because it is a contract tidy-up that the other stories do not depend on.

**Independent Test**: close a driver-backed resource from outside and confirm the connection is released; close a resource that holds nothing and confirm it is harmless; call `close` on a nested action's proxy and confirm it is refused while the proxy still satisfies the SQL resource contract.

**Acceptance Scenarios**:

1. **Given** a resource holding its own connection, **When** it is closed, **Then** the connection is released and a second close is harmless.
2. **Given** a resource that holds no connection, **When** it is closed, **Then** nothing happens and no error is raised.
3. **Given** a resource already closed, **When** it is opened again, **Then** opening and closing again are safe.
4. **Given** a nested action's proxy, **When** the nested action calls `close`, `open`, `begin`, `commit`, `rollback` or enters it as a context manager, **Then** each is refused as an operation belonging to the connection's owner.
5. **Given** that proxy, **When** it is checked against the SQL resource contract, **Then** it still satisfies the contract, and it exposes no way to acquire a connection.

---

### User Story 5 - The guidance explains the pair, and the pattern behind a per-call resource (Priority: P5)

A developer reads the connections chapter to decide how to declare a resource that must be created per call and must release something afterwards, and how to combine a process-wide pool with a per-call resource. The chapter explains that a per-call declaration is a mandatory pair — the factory creates, the finalizer closes — and adds a general section on keeping an expensive pool for the process while taking a connection only for one unit of work, with a table saying who opens and who closes in each of the three cases.

**Why this priority**: the framework now refuses a declaration that does not say how it is closed, and a reader who is not told why will read the refusal as an obstacle. It ranks with the library rather than after it: documentation ships with the change.

**Independent Test**: read the mode-2 section and the new section, and confirm the pair is stated, the two claims that contradict the code (a "fresh" resource per request, "no shared state between requests") are gone, the three-case table is present, and the worked example runs.

**Acceptance Scenarios**:

1. **Given** the connections chapter, **When** the mode-2 section is read, **Then** it states that the factory creates and the finalizer closes, that the finalizer may be synchronous or asynchronous, and that the boundary calls it after the run on success, on exception and on cancellation.
2. **Given** the same chapter, **When** it is searched for the claim that a per-call resource is always fresh or carries no shared state, **Then** neither claim is present.
3. **Given** the new section, **When** it is read, **Then** it shows the holder, the startup hook, the route and the resource, names the three cases and their openers and closers, states that the resource never closes the pool, and links to the Postgres page.
4. **Given** the worked example for the chapter, **When** it is run, **Then** it exits successfully without a live database and prints both the pool-backed and the DSN-backed case.

---

### User Story 6 - The demo shows the pattern end to end, and works without a database (Priority: P6)

A developer opens the demo to see the pattern in a whole application: a domain with a resource that reads and one that writes in a transaction, an action that declares the connection, a pool created at startup and closed at shutdown, and a route that declares the resource per call with both its factory and its finalizer. The demo starts and its tests pass without any PostgreSQL running.

**Why this priority**: the demo is how a reader copies the pattern rather than reconstructing it. It ranks last because it demonstrates the other five rather than adding capability.

**Independent Test**: install the demo without its database extra, run its test suite, and confirm it passes with no PostgreSQL running; then run it with a DSN and confirm concurrent calls do not fail, transactions do not interleave, the finalizer runs and the pool closes on shutdown.

**Acceptance Scenarios**:

1. **Given** the demo installed without its database extra, **When** the package is imported, **Then** nothing fails, because the database driver is an optional dependency and is not imported at package import time.
2. **Given** the demo's application started with no DSN, **When** a route is called, **Then** it answers through a connection stub and no pool is created.
3. **Given** the demo started with a DSN, **When** concurrent calls are made, **Then** none fails with the shared-connection error, no two transactions interleave, the finalizer runs for each call, and the pool closes when the application stops.

---

### Edge Cases

- A resource declared with both a connection description and a pool, or with neither: a construction error at declaration, not a failure at the first call.
- A resource created but never opened, and then closed: harmless.
- Opening a resource that is already open, and closing one that is already closed: both safe, and closing is idempotent so the second close does not return a connection twice.
- A pool that is exhausted when a request asks for a connection: the request waits, the wait ends in a named failure once the pool's timeout passes, and nothing is left half-open.
- An open that fails after some other resource of the same call was already opened: the ones already opened are still finalized.
- A failure inside the run and a failure while closing: the run's own failure is what the caller sees; the closing failure does not replace it.
- A failure while closing after a successful run: that failure surfaces, so a leaked connection is not silently reported as success.
- Cancellation of the task serving the call: the finalizer still runs and the connection still comes back.
- A nested action reaching the same resource: it receives the proxy, runs on the same connection, and cannot open, close, commit or roll back it.
- Rollup mode: a rollup run still rolls back instead of committing, on the connection its own resource holds.
- A pool-backed resource reaching a nested action: the nested action cannot return the connection to the pool, because only the boundary finalizes what it opened.
- Two pools in one process — as a test suite has: neither resource reaches the other's pool, and closing one leaves the other usable.
- A process where the pool is created but a resource was declared with its own connection parameters: the resource uses its own connection and the pool is never touched by it.
- A pool whose holder has not been filled yet — a request arriving during or before startup: the answer must be a named failure, not a failure to read an attribute that does not exist yet.
- A factory that returns one and the same shared resource on every call: the framework neither forbids nor detects it, the finalizer still runs exactly once per call, and the declaration owes a finalizer that is harmless on a shared object (Clarification).
- A transaction left open when the resource is closed: the resource rolls it back explicitly, returns the connection, and raises `TransactionLeftOpenError`; on a run that already failed, the run's error is what reaches the caller and the closing failure is recorded beside it (FR-020, FR-044).
- A pool's bounds and wait bound are stated in the code a reader copies — `min_size=1, max_size=10` where the pool is created and `30` where the wait happens, in the examples and the demo — so that the explicit statement is visible where the pattern is learned (Clarification).

## Requirements *(mandatory)*

### Functional Requirements

**The defect: one connection per unit of work**

- **FR-001**: A SQL resource that holds a connection MUST hold it for one unit of work only: it MUST NOT share that connection with any other resource or any other concurrent caller, and MUST NOT keep it after its unit of work has ended.
- **FR-002**: All operations of a resource that belong to the same transaction — starting it, running statements, committing and rolling back — MUST run on that resource's own held connection, so that no other caller's statement can run inside its transaction.
- **FR-003**: Two concurrent units of work MUST be able to use two different connections at the same time, under a declaration that serves both, and MUST NOT fail because another operation is in progress on a shared connection.

**Taking and returning the connection**

- **FR-004**: A resource MUST take its connection when it is opened, not when it is constructed, because construction is synchronous. Opening MUST guarantee that every later operation of that resource has a connection available.
- **FR-005**: A resource MUST be constructible in exactly two ways: from a connection description, in which case it opens its own connection, or with a ready pool keyword argument — a keyword, so that the two forms cannot be confused positionally — in which case it takes a connection from that pool. The connection description MUST default to absent, and supplying both descriptions, or neither, MUST be a construction error, raised when the resource is constructed.
- **FR-006**: Closing a resource that took its own connection MUST close that connection; closing one that took a connection from a pool MUST return it to the pool and MUST NOT close the pool. Closing MUST be harmless on a resource that holds no connection and on one already closed, and MUST NOT hand the same connection back twice.
- **FR-007**: A resource MUST NOT close a pool it was given, and MUST NOT reach a pool it was not given. No resource that was constructed without a pool may acquire connections from any pool.

**The process-wide pool**

- **FR-008**: The application MUST be able to create one pool for the process, from the same connection parameters a resource would use, and MUST close it when the application stops. Creating it MUST NOT happen per request.
- **FR-009**: The pool's lowest and highest number of connections MUST be stated when the pool is created, and the bound on waiting for a free connection MUST be stated explicitly where that wait happens — because the driver's pool creation accepts no such bound, and its default is to wait forever. Neither the driver's ten-connections-at-once floor and ceiling nor its unbounded wait MAY be inherited silently. The examples and the demo MUST carry `min_size=1, max_size=10` at creation and `30` as the stated wait bound, so the requirement is visible in the code a reader copies.
- **FR-010**: When the pool has no free connection, a request for one MUST wait, and the wait MUST end in a named failure once the stated bound passes, rather than waiting forever.
- **FR-011**: The number of connections held at any instant MUST NOT exceed the pool's stated ceiling.
- **FR-012**: The pool MUST be process state that the action does not receive as a connection: it MUST reach the route through the application's own holder, and an action's declared connections MUST NOT contain it.
- **FR-013**: Reading the holder before the pool exists MUST produce a named failure rather than a failure to read a missing attribute.

**Per-call declarations and what the boundary owns**

- **FR-014**: A per-call declaration MUST consist of a factory and a finalizer. The factory MUST run on every resolution and MUST return a resource; the finalizer MUST be the second parameter and MUST be mandatory, so that a declaration that creates a resource without saying how it is closed is rejected as incomplete. A parameter that is missing, or present but not callable, MUST be rejected when the declaration is validated. A factory that returns the same shared resource on every call MUST NOT be rejected, and MUST NOT be detected: the framework adds no marker and no comparison for it.
- **FR-015**: The finalizer MUST accept the resource created by the factory and MUST be allowed to be either synchronous or asynchronous — a callable returning either nothing or an awaitable of nothing — because returning a connection to a pool is asynchronous.
- **FR-016**: The boundary MUST open, before the run, those resources it created for this call that have a lifecycle, and MUST hand them to the run already open.
- **FR-017**: The boundary MUST call a declaration's finalizer exactly once after the run — in a finalization step that runs whatever the run did — on success, on exception and on cancellation alike. The boundary MUST have both the created resources and their finalizers in hand to do this, while the run itself continues to receive only the resources.
- **FR-018**: A resource with no lifecycle that is declared per call MUST still have its finalizer called exactly once; the boundary opens only what has something to open.
- **FR-019**: The boundary MUST open and close nothing that it did not itself create — a resource supplied ready remains the lifetime's to open and close.
- **FR-020**: An **operational** failure while closing — the release or the close of the connection itself failed — MUST NOT replace or hide the failure the run produced; on a run that otherwise succeeded, that failure MUST reach the caller. A contract violation found while closing is not an operational failure: FR-044 governs it, and there the opposite holds.
- **FR-021**: Finalizing what was opened MUST happen even when opening a later resource of the same call fails.
- **FR-022**: The run MUST continue to receive only the resolved resources, unchanged in shape: a per-call declaration MUST NOT change the mapping the machine receives.

**Closing in the contract, and nested actions**

- **FR-023**: Closing MUST be part of the SQL resource contract with a concrete harmless default on both the structural contract and the base resource, so that existing subclasses that hold no connection compile and behave unchanged with no edit. The default MUST be a real body, not a declaration that subclasses are obliged to fill in.
- **FR-024**: A resource supplied to a nested action MUST refuse `close`, `open`, `begin`, `commit`, `rollback`, and MUST refuse to be used as a context manager, so that a nested action cannot end or alter its owner's connection; it MUST NOT expose any way to acquire a connection, and MUST still satisfy the SQL resource contract.
- **FR-025**: The connection a nested action runs on MUST be the one its caller holds, so a nested call stays inside its caller's transaction and `rollup` keeps working.

**What stays as it is**

- **FR-026**: The public generic query surface MUST NOT be added to or removed in this feature; moving it to protected driver helpers is [#216](https://github.com/bystrovmaxim/aoa/issues/216). No new public query method MAY appear here. The home page's read examples that run through that surface MUST stay as they are: rewriting them belongs to [#216](https://github.com/bystrovmaxim/aoa/issues/216).
- **FR-027**: The existing transaction surface — beginning, committing, rolling back, and rollup mode rolling a commit back — MUST keep its behaviour, now on the connection its own resource holds.
- **FR-028**: Maxitor MUST NOT be touched by this feature; it already declares its shared object as a ready resource, having moved to mode 1 in [#213](https://github.com/bystrovmaxim/aoa/issues/213).

**Documentation, examples and the demo**

- **FR-029**: The connections chapter MUST explain the per-call pair — the factory creates, the finalizer closes — including that the finalizer may be asynchronous and that the boundary calls it after the run on success, on exception and on cancellation; and it MUST drop the claims that a per-call resource is always fresh and that it carries no shared state.
- **FR-030**: The connections chapter MUST gain a section named for a long-lived pool behind a per-call resource, placed after the chapter's "what to choose" guidance, on combining a process-wide pool with a per-call resource: the holder, the startup hook, the route and the resource, the table of who opens and who closes in each of the three cases, and the invariants — a pool can be shared, a resource cannot; the resource never closes the pool; the boundary opens only what it created for this call; the connection is taken when opening, not when constructed; exhaustion is bounded by the pool's timeout; the finalizer runs exactly once. It MUST be written so it applies to any pooled dependency, not only to the database driver, and MUST cross-link the Postgres page. It MUST close in the chapter's own style, with review questions and an exercise: replace the pool-backed resource with one that carries its own connection and say what changed in cost but not in correctness; and drop the timeout while the pool's ceiling is below the number of concurrent callers, and say what happens.
- **FR-031**: The Postgres page MUST describe the pool, opening and closing, who owns the connection, and that a transaction runs on the held connection with the transaction surface unchanged.
- **FR-032**: The resource-authoring page, the page that chooses among action, aspect and resource, and the package's own description of the SQL resource MUST match the new contract: closing among the obligations, the constructor's two forms, and the per-call pair. The package description MUST stop drawing a pool or connections that the implementation does not create.
- **FR-033**: The tutorial that describes the nested-action wrapper MUST state that the wrapper does not expose closing.
- **FR-034**: The worked examples for connections and for the resource MUST show the pool-backed per-call case with both the factory and the finalizer, and their notebooks MUST stay in step with the scripts.
- **FR-035**: Every example added or edited MUST run successfully with no live database, using a connection harness in place of a real one — the example runner executes every script and requires a zero exit code.
- **FR-036**: The demo MUST gain a domain that shows the pattern, **by extending its existing identity domain** with a Postgres resource that has a read method and a transactional method, an action declaring the connection, a pool created at startup for the service that has no request-scoped startup hook, and a route declaring the resource per call with both its factory and its finalizer. The domain MUST be described in its own README, and the demo's own README MUST be updated to match.
- **FR-037**: The database driver MUST be an optional dependency of the demo, declared as its own extra, so importing the demo without it does not fail, and the demo MUST run without a live database — through a connection harness, or a pool created only when a database description is supplied.
- **FR-038**: The demo MUST have its own tests covering: concurrent calls not failing, transactions not interleaving, the finalizer being called, and the pool closing on shutdown. Because the adapter's builder does not accept a startup hook today, the adapter MUST gain one general lifecycle option — the builder takes one asynchronous context manager that runs at startup and closes at shutdown — and the demo MUST install its pool's creation and closing there. A bound on the context manager's own closing and the order in which it runs relative to the application's shutdown MUST be stated by the adapter, and the option MUST NOT mention any database.
- **FR-039**: A stale-fragment sweep MUST be performed over the package and the documentation for the old shape — the single shared connection, direct connection creation outside opening, and per-call declarations with no finalizer — so that no fragment of the old usage remains.
- **FR-040**: The changelog MUST carry the article the constitution requires, under `## [Unreleased]` in both `packages/aoa-action-machine/CHANGELOG.md` and `packages/aoa-demo/CHANGELOG.md`, with a breaking-change section naming what replaces the single shared connection **and what the resource's constructor now is**, since the pool enters as a keyword and the rollup flag becomes keyword-only; and the domain README and the demo README MUST be updated with it. **A dated version heading is the maintainer's release act, not this feature's**: the version in package metadata names the version under development, so no dated heading and no version bump may be introduced here, and the existing `## [Unreleased]` content stays where it is, together with the new sections.

**Tests**

- **FR-041**: The declarations that build a per-call resource today MUST be migrated to the mandatory pair — the **five** that exist in the test suite (one in the FastAPI adapter's tests, three in the action machine's, one in the MCP adapter's) **and the one in the connections example script** — and no test or example may be left constructing a per-call declaration with one argument.
- **FR-042**: The connection harness used by the tests MUST reproduce the driver's one-operation-at-a-time rule, so that the concurrency test fails on the old shared-connection code and passes on the new code; the tests MUST supply a fake pool and a fake connection through the pool parameter, and no test may need a live database. The resource's own connection creation MUST be exercised by the examples and the demo rather than by a unit test, and the resource's constructor MUST NOT gain a substitution parameter for the tests' sake.
- **FR-044**: A resource MUST track whether a transaction is open: `begin` opens one, `commit` and `rollback` close it (`commit` in rollup mode closes it through `rollback`), and a failed `COMMIT` leaves it open, because the resource cannot claim the transaction ended. Closing a resource while a transaction is open MUST NOT rely on the driver's automatic rollback: the resource MUST issue the rollback itself and MUST return the connection to its pool or close it. It MUST then raise `TransactionLeftOpenError`, a subclass of `ResourceContractViolationError` — the family that means the caller's own code broke the resource contract. That error MUST be the one the caller sees, **including when the run had already failed**, with the run's error chained as its cause: it MUST NOT be recorded as a note instead of being raised, and no other closing failure MAY take its place. Returning the connection before raising is part of the requirement, not an aside — it is what keeps fail-fast from becoming a leak, and it preserves FR-017 and FR-021. A close on a resource that holds no connection, including a second close, raises nothing (FR-006). The one exception is cancellation: when the task serving the call is being cancelled, the `CancelledError` propagates and the violation is recorded beside it.
- **FR-043**: The adversarial check MUST be performed as usual: break the code so that exactly the new test goes red, confirm that no other check fails, and restore the code.

### Key Entities

- **Pool**: the process-wide store of reusable connections, created when the application starts and closed when it stops. It has a stated floor, a stated ceiling and a stated wait timeout. It may be shared by every caller; it is not itself a connection and is never handed to an action as one.
- **Resource**: the unit of work's handle on a database. It holds at most one connection, only for its own unit of work. It can be built from a connection description or from a pool, never both, never neither.
- **Unit of work**: one call's use of a resource — open, transact, close. Two units of work never share a connection, and their transactions never interleave.
- **Boundary**: the adapter serving the call. It creates per-call resources, opens those with a lifecycle before the run, and finalizes them after it on every path. It owns nothing supplied ready.
- **Per-call declaration**: the mandatory pair of a factory and a finalizer that describes a resource created for one call; the pair is what makes the resource's closure the framework's business rather than the developer's.
- **Finalizer**: what closes a resource created per call — synchronously or asynchronously — and returns a borrowed connection to its pool. It runs exactly once per call.
- **Nested-action proxy**: what a nested action receives in place of the resource its caller holds. It runs queries on the caller's connection and forbids every lifecycle operation, including closing.
- **Holder**: the application-scoped place that carries the pool to the routes, since the action does not receive the pool.

### Out of scope

- **The public generic query surface.** Moving it out of the SQL contract onto protected driver helpers is [#216](https://github.com/bystrovmaxim/aoa/issues/216) (FR-026). The documented read examples that go through it are rewritten there.
- **PgBouncer, and the server's own connection budget.** Neither the proxy configuration nor the database's connection ceiling is decided here.
- **Statement-cache modes.** How the driver caches prepared statements is untouched.
- **Retries and circuit breakers.** A failing connection or a failing statement is not retried here.
- **Maxitor.** It is not touched at all (FR-028); it moved to a ready resource in [#213](https://github.com/bystrovmaxim/aoa/issues/213).
- **Sessions, per-user state and several pools per process.** This feature allows one pool per application and does not decide how several would coexist.
- **Making the violation visible in an adapter's log or HTTP body.** Both adapters turn every uncaught exception into one generic server error and write nothing to the log, so the violation's message is read where the resource or the scope is driven directly — the tests, the demo's suite, whoever calls the resource — and in production it looks like an anonymous 500. Logging it is [#218](https://github.com/bystrovmaxim/aoa/issues/218), filed while writing this specification, and is not made here.
- **A general lifecycle for every resource kind.** The mechanism added here is the per-call pair and the closing obligation of the SQL contract; other resource families are not reshaped.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 30 concurrent calls under one declaration succeed at a rate of 100%, and the number that fail with a "another operation is in progress" interface error is 0 — measured against a harness that enforces the one-operation-at-a-time rule, so the check is red on the old code and green on the new.
- **SC-002**: Two concurrent transactions produce 0 interleaved statements and 0 rows committed by the wrong owner.
- **SC-003**: No request fails, and no row is written by another request, when the same declaration is served with and without a pool, so correctness does not depend on the pool.
- **SC-004**: The number of connections held simultaneously never exceeds the pool's stated ceiling, and the number of connections not returned after a call is 0, measured across a run of concurrent calls and across a run in which one call raises and one is cancelled.
- **SC-005**: A pool is created exactly once at startup and closed exactly once at shutdown, and closing a borrowed resource leaves the pool open and usable.
- **SC-006**: With a pool ceiling of 2 and 3 concurrent calls, the third completes after the others release their connections, and no call waits longer than the pool's stated timeout before receiving a named failure when a connection never frees.
- **SC-007**: A per-call declaration without a finalizer is rejected, and a declaration whose finalizer is not callable is rejected, in 100% of cases at declaration time.
- **SC-008**: The finalizer runs exactly once in 100% of success, exception and cancellation cases, and 0% of those cases leave a connection unreturned.
- **SC-009**: For an **operational** closing failure, a failing finalizer on an otherwise successful run makes the call fail, and a failing finalizer on a failed run leaves the original failure as what the caller sees — 100% of cases in both directions. A contract violation is excluded here; SC-023 governs it.
- **SC-010**: Closing a resource that holds no connection raises no error, and the existing subclasses that hold no connection pass with no edit.
- **SC-011**: A nested action's proxy refuses closing, opening, transaction control and context-manager use in 100% of cases, exposes no way to acquire a connection, and still satisfies the SQL resource contract.
- **SC-012**: Every SQL resource subclass in the repository and the demo still satisfies the contract after closing is added, with the stub subclasses unedited.
- **SC-013**: The whole existing test suite passes with no test edited except those this feature adds or migrates, and no check requires a live database; the number of per-call declarations still built with one argument is 0.
- **SC-014**: Every example and notebook added or edited exits successfully with no live database.
- **SC-015**: The demo installs and its suite passes with no database driver extra and no PostgreSQL running; with a database description supplied, its own tests for concurrency, transaction isolation, finalization and shutdown pool closure all pass.
- **SC-016**: A search of the package sources and the documentation for the old shape — the single shared connection, connect calls outside opening, per-call declarations without a finalizer — returns 0 stale fragments.
- **SC-017**: The repository's own check run finishes green, and the two accepted remarks are the only ones in the log.
- **SC-018**: Each of the four existing per-call declarations is migrated to the two-argument form and exercises the new lifecycle, measured by the migrated tests passing and by no remaining one-argument construction anywhere in the repository.
- **SC-019**: The new concurrency test is red on the old shared-connection code and green on the new code, and the adversarial break that produces the red makes no other check fail — both directions recorded, with the break restored afterwards.
- **SC-020**: The documentation touched by this feature names the pair, the three-case table, the section's placement and its exercise, and the demo's README describes its database-free mode; a reader checking those four points finds each one.
- **SC-021**: The adapter's builder accepts exactly one lifecycle option — an asynchronous context manager run at startup and closed at shutdown — and the adapter's own code names no database and no driver: a search of the adapter for the driver's types and for a pool, a DSN or a Postgres name returns 0 occurrences. What the adapter may still name is the framework's own connection vocabulary — it resolves connections and so it imports the type of a connection value — so the check is written against driver names, never against the word "connection".
- **SC-022**: A test that supplies a fake pool and a fake connection and never touches a database exists for the concurrency, exhaustion, cancellation and finalization checks, and the resource's public constructor carries no substitution parameter — measured by constructing it with exactly the two documented forms plus rollup, and no more.- **SC-023**: Closing with a transaction open returns the connection — 0 connections left unreturned — and raises `TransactionLeftOpenError` in 100% of such cases; on a run that already failed, the same close leaves the run's error as the raised one and records the closing failure, in 100% of cases. A second close of the same resource raises nothing and returns nothing twice.

- **SC-023**: Closing with a transaction open returns the connection — 0 connections left unreturned — and raises `TransactionLeftOpenError`; when the run had already failed, that error is **still** the raised one and the run's error is its cause, in 100% of cases, and it is never demoted to a note. A second close of the same resource raises nothing and returns nothing twice. Under cancellation the `CancelledError` still propagates and the violation is recorded beside it.

## Assumptions

- The defect is real and reproducible only under concurrency, so the tests need a connection harness that enforces the one-operation-at-a-time rule and a fake pool reached through the pool parameter; otherwise no test can go red on the old code, and no test may need a live database. The resource's public constructor is not widened for the tests' sake.
- The framework does not create, configure or close a pool, and it does not police what a per-call factory returns: the pool is the application's object, and the factory's return is the declaration's affair. The framework supplies the place where the application's startup and shutdown code runs, and the lifecycle around a resource created per call.
- "The boundary" is the adapters: the FastAPI adapter and the MCP adapter, at the points where they resolve connections before running the machine. The MCP service has no request-scoped startup hook, so its pool is created when the service starts — through the one general lifecycle option the adapter gains (FR-038), which runs a context manager at startup and closes it at shutdown and knows nothing about databases.
- Readiness of the resource is the framework's existing convention: a resource is ready when it is supplied directly, and per-call when it is declared with a factory. The finalizer is what the per-call form was missing.
- The resource's constructor shape is `(connection_params=None, *, pool=None, rollup=False)`: the connection description keeps its default-empty position, the pool enters as a keyword, and rollup keeps its place. This is the shape the issue states, and it is the shape the "exactly one of the two" rule is checked against.
- The pool is deliberately not part of an action's connections, because the action does not use it. The holder is application-scoped state beside the application, not domain state.
- One pool per application is enough for the pattern this feature documents; several pools in one process are outside the scope, though the tests will have more than one application.
- The version already in the package's metadata is the version this work releases; the alternative — bumping past it — is not taken, because releasing what the metadata claims is what makes the metadata honest.
- The project constitution applies: English in commits, in git and in code; module headers; machine-readable blocks on public classes; one-line docstrings; documentation written with the change; a Russian draft beside every page the maintainer reads; and the closing check run taken to zero, followed by the documentation and then the changelog, as the last three steps of the work.
- Documentation ships with the change it describes, and the examples run: a page written for this feature is reported together with its Russian draft beside it, and every script under `examples/` is executed with the repository's own environment before the work is called finished.
