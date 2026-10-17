# Feature Specification: The query surface leaves the SQL contract, and the driver keeps protected helpers

**Feature Branch**: `feature/issue-216-sql-contract-driver-helpers`

**Created**: 2026-10-17

**Status**: Draft

**Input**: User description: "https://github.com/bystrovmaxim/aoa/issues/216 — `execute(query, params=None)` sits in the SQL contract and is therefore imposed on every SQL resource, while the framework itself never calls it. The query surface leaves the public contract; the driver keeps protected helpers for its subclasses, and a nested action cannot reach the connection at all."

## Clarifications

### Session 2026-10-17

- Decision carried over from the issue: **the generic query member leaves the public contract.** `execute` is an obligation on every SQL resource that nothing in the framework needs, and it pushes a generic SQL passthrough onto resources whose point is semantic transport (`read_balance`, `post_transfer`). The member is removed from the structural contract, from the base resource and from the nested-action proxy, and it becomes a protected member of the driver.
- Decision carried over from the issue: **the driver keeps protected helpers, and they are the extension point.** A domain resource runs its statements through the driver it holds — `_execute` for a statement, `_fetchrow` for a row — and neither the "connection is open" check nor the generic wrapping of a driver failure appears in domain code any more. Today the same check is written four times in `PostgresResource` (`begin`, `commit`, `rollback`, `execute`); after this feature it is written once, in `_require_connection`.
- Decision carried over from the issue: **a nested action cannot reach the connection at all, by construction rather than by a rule.** With no delegation left, the proxy a nested action receives has no query member to call; a domain that wants nested access overrides `get_wrapper_class()` with its own wrapper that delegates its own semantic methods, the pattern `OcelStoreWrapper` already follows in `aoa-ocel`. `SqlResource.get_wrapper_class()` keeps returning `WrapperSqlResource` as the safe default, and `isinstance(wrapper, ProtocolSqlResource)` must stay true after the contract shrinks.
- Decision carried over from the issue: **the demo exercises the helpers**, so the pattern is demonstrated in `packages/` and every helper has a real caller there. The issue adds that `vulture` would fail on an uncalled helper; that premise does not hold, and the clarification session records the measurement — the dead-code check runs at a confidence that does not report an unused method, so what shows the rule was kept is the search over the branch base (SC-012), not the check.
- Decision carried over from the issue: **removing the member is a breaking change for every SQL resource outside this repository**, and the changelog must name the replacement: a domain resource runs statements through the protected helpers on the driver it holds, and a generic passthrough, if someone still wants one, is that resource's own public method rather than a framework default.
- Decision taken in the clarification session: **exactly two helpers, and the repository's own reading becomes one of them.** The issue names two — the statement path and the row path — and requires the demo to demonstrate both. The demo's only read, `IdentityStore._fetch_rows` (added by [#215](https://github.com/bystrovmaxim/aoa/issues/215)), returns several rows and reaches `self._conn.fetch(...)` behind its own check, which raises `RuntimeError` rather than `HandleError`; keeping it would leave a multi-row helper with no second caller anywhere and an unreachable read path. The maintainer chose to reshape that read into a single-row one, so both helpers have a caller inside `packages/`, the API stays at the two members the issue names, and nothing speculative is added. What the reshaping costs is stated in the requirements (FR-015, FR-016) and in Out of scope.
- Decision taken while writing this specification: **the demo's driver-free base keeps its own storage primitives.** `IdentityStoreBase.record_login` calls the public `self.execute(...)`; that call is the only use of the removed member anywhere under `packages/`, and it is the demo's own code rather than the framework's. The base declares the write primitive it needs beside the read primitive it already declares, the PostgreSQL store implements both through the driver's protected helpers, and the in-memory store implements them without a driver. The domain keeps one transaction, written once.
- Decision taken while writing this specification: **the issue's list of demo stubs is two modules short, because the issue was written before #215 landed.** Besides the eight stubs the issue names, `identity_store_stub.py` carries the removed member and `identity_store_base.py` calls it. Planning works from the code, not from the issue's list.
- Decision taken while writing this specification: **the line numbers the issue cites have drifted, and the specification does not carry them.** #215 rewrote `docs/extensions/postgresql.md` (683 lines in the merge) and `PostgresResource` — `execute` sits at `postgres_resource.py:223`, not `:136`. Every site is named by member and by page; planning re-locates each one before editing it.
- Decision taken while writing this specification: **the changelog follows #215's correction, not the issue's wording.** The issue asks for "a version bump and a dated entry (`## [version] – YYYY-MM-DD`)". In [#215](https://github.com/bystrovmaxim/aoa/issues/215) the maintainer corrected exactly this reading: a version in package metadata names the version **under development**, and the dated heading is the maintainer's release act, not a feature's. The article therefore goes under `## [Unreleased]` in `packages/aoa-action-machine/CHANGELOG.md`, with a `### Breaking changes` section, and no dated heading and no version bump are introduced here. Recorded as a decision so that one word from the maintainer overturns it.
- Decision taken while writing this specification: **the specification uses the library's own vocabulary** — contract, resource, driver, helper, wrapper, nested action, unit of work — because this feature *is* that vocabulary. It is not written in end-user terms, and the member shapes the issue states are requirements rather than choices left to planning. Clarification markers are therefore used only where the issue leaves a decision genuinely open; today there are none.

### Session 2026-10-17 — clarification

- Q: Should the breaking change ship as a dated release entry with a version bump, or as an article under `## [Unreleased]`? → A: **Under `## [Unreleased]` in `packages/aoa-action-machine/CHANGELOG.md`, with no dated heading and no version bump** — the maintainer confirmed the #215 correction rather than the issue's wording, so FR-030 and SC-014 stand as written.
- Q: Does the removal keep any compatibility for the library users outside this repository who call the member? → A: **No — a clean break.** The member is gone from the structural contract, from the base resource and from the proxy, with no alias, no override that outlives it and no deprecation window; the changelog is the only place the replacement is named. FR-001 … FR-004, FR-011 and SC-001 stand as written.
- Q: Which protected helpers does the driver offer? → A: **Exactly two — `_execute` for a statement and `_fetchrow` for a row — and the demo's own read is reshaped to a single row so that both have a caller inside `packages/`.** `_fetch` and `_fetchval` are not added: after the reshaping no domain method in the repository reads several rows or a single value, and the issue's rule is that such a helper appears only when a caller does. Measured while deciding, because the issue's premise does not hold: the repository runs `vulture` with `min_confidence = 80`, and an unused method carries 60 % confidence, so an uncalled helper would **not** fail the check run (measured on a scratch file: exit 0 at 80, `unused method … (60% confidence)` at 60). "No speculative API" is therefore the maintainer's rule rather than something the check enforces; what the check does catch is an unused import — the `Any` the demo stubs lose. Also measured: `fetchrow` is the same driver call as `fetch` with the protocol's row cap set to one (`connection.py`: `_execute(query, args, 1, …)` against `fetch`'s `0`), so it appends no `LIMIT` to the statement, shares the same prepared statement, and cannot be slower; its hazard is semantic, not performance — it returns the *first* row, so a query that can match several rows without an ordering silently yields an arbitrary one, which the guidance must say.
- Q: Where does the pair of storage operations live in the demo's driver-free base — in the base as primitives each store implements, or pushed down into each store as its own two methods? → A: **In the base, as primitives each store implements**, so that the transaction protocol stays in one place and the in-memory store never has to interpret a statement. The decisive evidence is the code the removed member produced: the in-memory store decides what to do by testing the statement text for an insert (`identity_store_stub.py`: `query.lstrip().upper().startswith("INSERT")`), and only a primitive that already carries the domain's meaning removes that. Pushing both operations down would duplicate `begin`/`commit`/`rollback` across two stores and make the in-memory transaction pure ceremony. Recorded in FR-015, FR-016 and SC-017.
- Q: Should the tutorial case whose whole subject was the proxy running a query be rewritten in place, or deleted? → A: **Deleted — script, notebook and tutorial section — and its surviving half moves into the nested-action case.** A case cannot be rewritten when the member it exists to demonstrate is gone; deleting it costs the reader nothing, since the neighbouring cases already carry the refusals, and the case that remains is where the runtime supplies the proxy and where a resource's own wrapper delegating its own semantic method can be shown for real. The later cases keep their numbering, so the deletion leaves a gap rather than moving every later notebook. Recorded in FR-022, the nested-action edge case and SC-018.

## User Scenarios & Testing *(mandatory)*

The readers of this feature are a library user who subclassed a SQL resource, a developer writing a domain resource over the driver, a developer whose nested action was reaching the connection, and a reader of the pages that taught the passthrough.

### User Story 1 - A SQL resource is obliged to offer a lifecycle, not a query passthrough (Priority: P1)

A developer subclasses the SQL resource contract and implements what the framework actually asks of a resource: open, begin, rollback, and `commit` from the base. Nothing obliges them to publish a `query, params` passthrough that the framework never calls, and the resources whose point is semantic transport state their own methods and nothing else. The eight demo stubs stop carrying a method that only ever returned a no-op.

**Why this priority**: this is the change itself. Everything else in the feature exists to make the removal usable — the helpers that replace it, the proxy that no longer shows it, the documentation that taught it. Until the member leaves the contract, the obligation stands.

**Independent Test**: define a SQL resource subclass with `open`, `begin` and `rollback` only, instantiate it, and run the repository's own suite: it passes, the subclass publishes no query member, and a search for a definition of the member in the contract and in the public SQL resources returns nothing.

**Acceptance Scenarios**:

1. **Given** the structural contract, **When** its members are listed, **Then** it names the lifecycle and no generic query member.
2. **Given** the base resource, **When** a subclass implements only `open`, `begin` and `rollback`, **Then** it is instantiable and `commit` comes from the base.
3. **Given** the eight demo stubs, **When** they are read, **Then** none of them defines the member, and none imports `Any` for its sake.
4. **Given** the whole repository, **When** a search for a public query member on a SQL resource is run, **Then** it returns nothing under `packages/`.

---

### User Story 2 - A domain resource runs statements through the driver's protected helpers (Priority: P2)

A developer writes a semantic method on a resource over PostgreSQL — `mark_seen`, `record_login`, `read_person` — and calls a protected helper for the statement and one for the read. The helper checks that the connection is open and names the failure when it is not, and it turns any driver failure into the framework's own error with the driver's error chained, so the domain method carries its business meaning and no transport mechanics. A domain method that wants its own context wraps it deliberately, in one `except`.

**Why this priority**: the helpers are what makes the removal survivable. Without them, every domain resource would reach for the connection itself — which is the reach-through the wrapper exists to prevent — and every one of them would repeat the same two checks.

**Independent Test**: call each helper on a resource that is not open and confirm the named failure; make the connection raise and confirm the failure arrives as the framework's own error with the driver's error chained; run a statement and a read through a real domain method and confirm the result.

**Acceptance Scenarios**:

1. **Given** a resource that is not open, **When** a helper is called, **Then** the failure is the framework's own named failure rather than a failure to read a missing attribute.
2. **Given** an open resource whose connection refuses the statement, **When** the helper is called, **Then** the framework's own error arrives with the driver's error chained as its cause.
3. **Given** a transactional domain method, **When** it runs a statement through the helper, **Then** the statement lands on this unit of work's own connection and inside its transaction, and rollup mode rolls the whole thing back.
4. **Given** a domain method that reads one row, **When** it reads it, **Then** it goes through the row helper rather than reaching for the connection, and a failure is named as in (1) and (2).
5. **Given** the same check that today appears in `begin`, `commit`, `rollback` and the query member, **When** the driver is read, **Then** it appears once and the three lifecycle members use it.

---

### User Story 3 - A nested action cannot reach the connection at all (Priority: P3)

A nested action receives a proxy, and the proxy offers neither the public member nor a protected one, so there is nothing for a nested action to run a statement with — by construction, not by a refusal it could be taught to bypass. A domain that does want to hand a nested action something overrides the wrapper class with its own, delegates its own semantic methods, and keeps refusing the lifecycle; `isinstance(proxy, ProtocolSqlResource)` stays true, so the framework's own checks keep passing.

**Why this priority**: the refusal was the old answer, and it depended on the framework noticing a call. The absence is the stronger answer: a nested action cannot misuse what it has never been given. It ranks below the removal itself because it follows from it.

**Independent Test**: build a proxy over a resource, confirm that neither the public member nor the helpers are reachable on it, that the lifecycle and closing are still refused, and that the proxy still satisfies the contract; then build a domain wrapper that delegates one semantic method and confirm the nested path works while the lifecycle stays refused, including through a second and a third wrap.

**Acceptance Scenarios**:

1. **Given** a nested action's proxy, **When** the query surface is looked for on it, **Then** neither the public member nor a protected helper exists there.
2. **Given** the same proxy, **When** `open`, `begin`, `commit`, `rollback`, `close` or context-manager use is attempted, **Then** each is refused as an operation belonging to the connection's owner.
3. **Given** the same proxy, **When** it is checked against the contract, **Then** it satisfies the contract and exposes no way to acquire a connection.
4. **Given** a domain wrapper that delegates its own semantic method, **When** a nested action calls it, **Then** the call runs on the caller's connection and inside its transaction, while the lifecycle stays refused.
5. **Given** two and three levels of wrapping, **When** the innermost proxy is used, **Then** the refusals and the contract hold exactly as at the first level.

---

### User Story 4 - The demo lives the pattern, and still runs without a database (Priority: P4)

A reader opens the demo's identity domain — the one [#215](https://github.com/bystrovmaxim/aoa/issues/215) added — and finds the pattern to copy: the domain's two operations are written once on a driver-free base, the PostgreSQL store implements its storage primitives through the driver's protected helpers, and the in-memory store implements the same primitives without a driver. The demo installs, imports and passes its suite with no PostgreSQL running and no driver extra installed.

**Why this priority**: the demo is how a reader copies the pattern instead of reconstructing it, and it is what gives each of the two helpers a caller inside `packages/`, so no member of the helper set is speculation. It ranks below the contract work because it demonstrates it.

**Independent Test**: install the demo without its database extra, run its suite and confirm it passes with no PostgreSQL running; read the identity store and confirm that both operations reach storage through the domain's own primitives, whose PostgreSQL implementation uses the protected helpers.

**Acceptance Scenarios**:

1. **Given** the driver-free base, **When** its two operations are read, **Then** neither calls a public query passthrough, and each reaches storage through a primitive the base declares.
2. **Given** the PostgreSQL store, **When** its primitives are read, **Then** the write goes through the statement helper and the read through the row helper, with no direct use of the connection in the domain.
3. **Given** the in-memory store, **When** it is read, **Then** it implements the same primitives and defines no public query member.
4. **Given** the demo installed without its database extra, **When** the package is imported and its suite is run, **Then** nothing fails and no test needs a database.
5. **Given** a resource that is not open, **When** the demo's read runs, **Then** the failure is the framework's named failure rather than the base's own `RuntimeError`.
6. **Given** the demo's read, **When** nobody matches, **Then** it answers nothing rather than an empty collection, and the route's own two outcomes — the person or not — are unchanged.

---

### User Story 5 - The pages teach semantic methods instead of a generic passthrough (Priority: P5)

A developer reads the PostgreSQL page, the authoring pages and the home page, and learns the shape the feature establishes: the contract is a lifecycle, the driver exposes protected helpers to its subclasses, a domain resource states its own semantic methods, and a passthrough is something a resource may choose to publish itself. The example case whose whole subject was the proxy delegating the generic member is deleted rather than rewritten — its subject no longer exists — and the pattern that replaces it, a resource's own wrapper delegating its own semantic method, is demonstrated in the nested-action case, which is where the runtime supplies the proxy.

**Why this priority**: documentation ships with the change, and a reader who is not told why the member left will read the removal as a loss rather than as the point. It ranks with the library, below the code it describes.

**Independent Test**: read the named pages and confirm that none presents the removed member as the SQL query surface; run every example that was edited and confirm it exits successfully with no live database.

**Acceptance Scenarios**:

1. **Given** the PostgreSQL page, **When** its query-surface paragraph is read, **Then** it describes the protected helpers and their two shapes rather than a public passthrough, and a domain resource's own row-reading methods are stated as its own.
2. **Given** the resource-authoring page, **When** it is read, **Then** it names the helpers as the way a domain resource runs a statement, and it no longer says the proxy delegates the removed member.
3. **Given** the page that chooses among action, aspect and resource, **When** it describes the proxy, **Then** it does not claim the proxy executes commands.
4. **Given** the home page, **When** its SQL resource example is read, **Then** it no longer teaches a resource calling the removed member on the driver as the ordinary way to write SQL.
5. **Given** the tutorial's case that demonstrated a query through the proxy, **When** the tutorial is read, **Then** the case and its notebook are gone, the section states that the proxy offers nothing to run a query with, and the nested-action case that remains demonstrates a resource's own wrapper delegating its own semantic method while the lifecycle stays refused — and it exits successfully with no live database.

---

### User Story 6 - A library user learns what broke and what replaces it (Priority: P6)

A user who subclassed a SQL resource outside this repository reads the package changelog and finds the change named where they will look for it: the member is gone from the contract, and the replacement is stated in one sentence — a domain resource runs statements through the protected helpers on the driver it holds, and a generic passthrough is that resource's own public method if it still wants one.

**Why this priority**: removing a member from a published contract without naming the replacement is how a library loses its users' trust, and the changelog is the only place a user sees it. It ranks last because it is the report of the change rather than the change.

**Independent Test**: read the package changelog and confirm the change appears once, in the breaking-change section, with the replacement named; confirm that the change has no dated heading of its own.

**Acceptance Scenarios**:

1. **Given** the package changelog, **When** the unreleased section is read, **Then** a breaking-change entry states that the query member left the public contract and names the helpers and the resource's own method as the two replacements.
2. **Given** the same entry, **When** the release headings are listed, **Then** no new dated heading and no version bump were introduced by this feature.
3. **Given** the release the issue asks in words, **When** the maintainer reads this specification, **Then** the decision to keep the article unreleased is stated where it can be overturned in one word (Clarifications).

---

### Edge Cases

- A helper called on a resource that was never opened: the framework's named failure, never an attribute error on a missing connection.
- A helper called after the resource is closed: the same named failure, because the connection is gone.
- A helper called on a resource whose connection is present but refuses the statement: the framework's own error with the driver's error chained as its cause, never the driver's error reaching the caller raw.
- Parameters: a statement with no parameters and a statement with parameters take the same path, and an empty sequence is treated as no parameters.
- A domain method that wants its own message: it catches the framework's error and raises its own with that error as the cause, which is a deliberate act and not what the helper does by default.
- A domain resource over a driver it does not hold — the in-memory store: it implements the domain's primitives without the helpers, and defines no public query member either.
- The row helper answers the *first* row, not the *only* one: a query that can match several rows without an ordering yields an arbitrary one, silently, and no error says so. The guidance must state the hazard, and a domain method whose query is not unique is the domain's own responsibility rather than something the helper detects.
- The deleted example case leaves a gap in a numbered tutorial: the examples are discovered by walking the directory, so nothing breaks, and the later cases keep their numbers rather than being renumbered — a renumbering would rename every later notebook and rewrite every link to it, which is churn the reader pays for and gains nothing from.
- The nested-action case carries two claims at once after the change: the wrapper the runtime supplies refuses the lifecycle, and the resource's own wrapper still serves its own semantic method. A case that shows only one of the two leaves the other to be guessed.
- The demo's read answers one person or nothing: the two outcomes the route reported before are unchanged, but a test that asserted a collection is a test this feature migrates together with the domain.
- A resource that never had the removed member at all — a stub that holds no connection — handed to a nested action: the proxy still satisfies the contract, and there is nothing to call.
- A domain wrapper that delegates a semantic method and forgets to refuse the lifecycle: the base wrapper's refusals are still what the framework hands out by default, and the domain wrapper is the domain's responsibility.
- Two and three levels of wrapping: the innermost proxy is still a contract-satisfying proxy with no query member.
- Rollup mode: a transactional domain method that runs statements through the helpers still rolls its commit back.
- A transaction left open when the resource is closed: unchanged from [#215](https://github.com/bystrovmaxim/aoa/issues/215) — the resource ends it, returns the connection, and raises the contract violation.
- A helper with no caller inside `packages/` is a defect rather than a courtesy, and the rule is the maintainer's rather than the check's: the repository's dead-code check runs at a confidence that does not report an unused method, so what shows the rule was kept is the search over the branch base, not the check (Clarifications, SC-012).
- A resource class in this repository that publishes its own `execute` for its own semantics — an in-memory ledger, an OCEL store: it is untouched, because it is a resource's own method and not the SQL contract.

## Requirements *(mandatory)*

### Functional Requirements

**What leaves the public contract**

- **FR-001**: The structural SQL contract MUST NOT declare a generic query member, and MUST NOT list one among its members in its own description.
- **FR-002**: The base SQL resource MUST NOT declare a generic query member, abstract or concrete; its own description, its contract line and its architecture diagram MUST name the lifecycle it actually offers, and its rollup walk-through MUST NOT show a statement being written through a member that no longer exists.
- **FR-003**: The nested-action proxy MUST NOT declare a generic query member and MUST NOT delegate one; its own description MUST match.
- **FR-004**: No public SQL resource under `packages/` — the driver, the base, the proxy — MAY declare a generic query member, and a SQL resource subclass MUST be instantiable while implementing only `open`, `begin` and `rollback`, with `commit` taken from the base.

**What stays, protected**

- **FR-005**: The driver MUST offer its subclasses a protected helper for running a statement, returning the driver's command status, and a protected helper for reading a single row; both MUST be documented as the extension point, and both MUST carry the one-line docstrings the constitution requires.
- **FR-006**: The "connection is open" check MUST exist in exactly one place on the driver, and `begin`, `commit`, `rollback` and every helper MUST use it; the failure it raises MUST be the framework's own named failure, so a closed or never-opened resource never surfaces an attribute error.
- **FR-007**: Every helper MUST turn a failure of the driver into the framework's own error with the driver's error chained as its cause, so a domain method never has to name the driver's exception types and the driver's own error never reaches the caller raw.
- **FR-008**: The helpers MUST be exactly the two the issue names — a statement path and a row path — and each MUST have a caller inside `packages/` after this feature, so that no member is added on speculation. A helper for several rows or for a single value MUST NOT be added; if a domain method in this repository grows such a need later, the helper is added then, with that caller.
- **FR-009**: A domain method that wants its own failure message MUST be able to wrap the helper's error deliberately, in one `except`, with the helper's error chained as the cause. That wrapping MUST NOT be done by the helper itself.
- **FR-010**: The helpers MUST run their statement on the connection the resource holds for its unit of work, so a statement issued by a domain method stays inside that unit of work's transaction and respects rollup mode.

**The proxy, and nested access**

- **FR-011**: A resource handed to a nested action MUST expose neither the removed public member nor any protected helper, so a nested action has no way to run a statement of its own; and the proxy MUST still satisfy the structural contract.
- **FR-012**: The proxy MUST keep refusing `open`, `begin`, `commit`, `rollback`, `close` and context-manager use, and MUST NOT expose any way to acquire a connection. These refusals are unchanged by this feature.
- **FR-013**: A resource MAY override the wrapper class it hands to nested actions with its own proxy that delegates its own semantic methods; the base MUST keep returning the default proxy, and the domain pattern MUST be documented as the way nested access is given when it is wanted.

**The demo**

- **FR-014**: The eight demo stubs that override the removed member MUST lose the member and any import that existed only for it, and MUST need no other edit.
- **FR-015**: The demo's identity domain MUST run its storage through primitives the driver-free base declares: a read primitive that returns one person or nothing, and a write primitive beside it. `record_login` MUST NOT call a public query passthrough, and the base MUST keep one transaction for its two operations. This reshapes the domain's read — today it returns a list of rows — and the reshaping is the price of keeping the helper set at the two members the issue names and giving both a caller (Clarifications).
- **FR-016**: The PostgreSQL identity store MUST implement those primitives through the driver's protected helpers — the read through the row helper, the write through the statement helper — and MUST NOT reach for the connection from the domain; the in-memory store MUST implement the same primitives without a driver and MUST publish no public query member. The in-memory store MUST NOT inspect the text of a statement to decide what to do: today it sniffs the statement for an insert, and that sniffing is the artifact the removed member created in a store that has no SQL. The demo's own read MUST keep converting the driver's row type into a plain mapping at that boundary, and MUST raise the framework's named failure rather than its own error when the resource is not open.
- **FR-017**: The demo MUST install, import and pass its own suite with no database driver extra and no PostgreSQL running.

**Documentation and examples**

- **FR-018**: The PostgreSQL page MUST replace its query-surface paragraph with the protected helpers and their shapes, and MUST state that a domain resource supplies its own row-reading methods.
- **FR-019**: The resource-authoring page MUST name the protected helpers as the way a domain resource runs a statement, and MUST NOT state that the proxy delegates the removed member.
- **FR-020**: The page that chooses among action, aspect and resource MUST NOT claim that the proxy executes commands.
- **FR-021**: The home page MUST stop presenting a resource calling the removed member on the driver as the ordinary way to write SQL, and MUST show the semantic-method shape instead.
- **FR-022**: Every example, notebook and page that presented the removed member as the SQL query surface MUST be rewritten. The one case whose whole subject was the proxy delegating that member MUST be deleted with its notebook and its tutorial section, because the subject no longer exists; its surviving half — what a nested action can be given instead — MUST be demonstrated in the nested-action case, where the runtime supplies the proxy and where the resource declares its own wrapper delegating its own semantic method, with the lifecycle still refused. The remaining examples keep their numbering, so the deleted case leaves a gap rather than moving every later notebook and link. The Russian draft of a rewritten page MUST be updated beside it.
- **FR-023**: Every example and notebook added or edited MUST run successfully with no live database, using a recording connection or pool in place of a real one; the example runner executes each script and requires a zero exit code.
- **FR-024**: The unrelated `execute` methods of custom domain resources MUST NOT be touched — an in-memory ledger or an OCEL store keeps its own method and its own name. The pre-AOA code shown in the legacy-migration page MUST be checked separately and rewritten only if it presents the removed member as the framework's query surface.

**Tests**

- **FR-025**: Tests that build an incomplete SQL resource MUST use `begin`/`rollback` rather than the removed member to prove incompleteness, and tests that delegate the removed member through the proxy MUST be replaced by tests that assert the query surface is absent from the proxy and that a domain wrapper delegates its own semantic method.
- **FR-026**: The existing tests and the demo's tests that call the removed member on a resource MUST be migrated to the protected helpers, and no test or example may be left calling it.
- **FR-027**: The tests this feature adds MUST cover: a helper on a closed resource raising the framework's named failure rather than an attribute error; a driver failure arriving as the framework's error; the proxy exposing no query member of either kind while still satisfying the contract; a domain wrapper delegating its own method and still refusing the lifecycle, at two and three levels of wrapping; a resource subclass needing only `open`, `begin` and `rollback`; the contract check staying true after the shrink; and the demo's in-memory store implementing the domain's primitives. No test may need a live database.
- **FR-028**: The adversarial check MUST be performed as usual: break the code so that exactly the new tests go red, confirm that no other check fails, and restore the code.

**The tail the constitution requires**

- **FR-029**: The documentation MUST be written after the code is settled, and MUST show every shape the feature introduces rather than one happy path: the driver's helpers, the closed-resource failure, the wrapped driver failure, the domain method, the proxy that has nothing to call, and the domain wrapper that delegates its own method. Each case MUST appear as a runnable script and as a notebook, and each MUST be executed while it is written.
- **FR-030**: `packages/aoa-action-machine/CHANGELOG.md` MUST gain the article the constitution requires, under `## [Unreleased]`, with a `### Breaking changes` section stating that the generic query member left the public SQL contract and naming the replacements — the protected helpers on the driver a domain resource holds, and the resource's own public method for anyone who still wants a passthrough. No dated release heading and no version bump may be introduced, and the demo's changelog MUST gain a line only for what its own public surface lost.
- **FR-031**: The plan MUST reserve exactly three closing tasks in the constitution's order — the check run taken to zero, then the documentation, then the changelog — and no other task may absorb them.

### Key Entities

- **SQL resource contract**: what every SQL resource is obliged to offer. After this feature it is the lifecycle — open, begin, commit, rollback, close — and rollup, and it no longer contains a query member.
- **Driver**: the concrete SQL resource that holds a connection and talks to the database. It is the only place that knows how a statement is run and what the connection's own error looks like.
- **Protected helper**: a member the driver offers its subclasses and nobody else — the statement path, the row path, and the one connection check they share. Not part of the contract, never reachable through the proxy, and documented as the extension point.
- **Nested-action proxy**: what a nested action receives in place of the resource its caller holds. It refuses every lifecycle operation and now offers nothing to run a statement with, so nested access to the connection is impossible rather than forbidden.
- **Domain wrapper**: a resource's own proxy, substituted through the wrapper class, that delegates the resource's semantic methods to nested actions while the lifecycle stays refused. `OcelStoreWrapper` is the existing example.
- **Semantic method**: a domain operation on a resource — `read_person`, `record_login`, `mark_seen` — written in the domain's words and implemented through the protected helpers. It is what replaces the passthrough as the resource's public surface.
- **Driver-free storage primitive**: the pair of operations a driver-free base declares so that the same domain runs over PostgreSQL and in memory — a read that answers one row or nothing, and the write beside it. The driver's own row type stops at the PostgreSQL store, which converts it to a plain mapping.
- **Unit of work**: one call's use of a resource. A statement run through a helper belongs to the resource's own unit of work and to its transaction.

### Out of scope

- **The lifecycle changes of [#215](https://github.com/bystrovmaxim/aoa/issues/215).** Closing, the pool-backed constructor, the per-call pair and the fail-fast transaction rule have landed; this feature changes none of them and only has to keep them working.
- **A generic passthrough, anywhere.** This feature does not add one under another name, and it does not add a compatibility shim that keeps the old member callable: the removal is the point.
- **Speculative helpers.** A helper for a value, a row set, or a streaming read is added only when a caller in this repository needs it; the rule is kept by the search over the branch base rather than by the dead-code check, which does not report an unused method at the confidence this repository runs it (Clarifications, SC-012).
- **Other resource families.** The external-service resource and its proxy, the OCEL store and its wrapper, and every custom resource that publishes its own `execute` are not reshaped; the OCEL wrapper is cited as the pattern to copy, not migrated.
- **The demo's behaviour.** Nothing a demo route answers changes: the same domain, the same route, the same database-free mode, the same two outcomes — a person found or not found. The one exception is the shape the domain's read answers in: `read_person` returns one person or nothing rather than a list of rows, because that is what gives the driver's row helper its caller (FR-015, Clarifications). The route's answer is unchanged; only the domain's own read shape and the code around it move, and no other demo behaviour is touched.
- **The adapter logging gap.** A contract violation or a wrapped driver failure is still invisible through the transport; that is [#218](https://github.com/bystrovmaxim/aoa/issues/218).
- **Maxitor.** It is not touched; it declares a ready resource rather than subclassing the SQL contract for a generic passthrough.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A search over the package sources and the adapters for a public query member on a SQL resource returns 0 definitions, and a search for a call of the removed member anywhere under `packages/` returns 0 — the driver's own calls on its held connection excepted, since those are not calls of the contract's member.
- **SC-002**: A SQL resource subclass that implements only `open`, `begin` and `rollback` instantiates and runs in 100% of the incomplete-subclass tests, with `commit` taken from the base.
- **SC-003**: Each protected helper, called on a resource that never opened and on one already closed, produces the framework's named failure in 100% of cases and an attribute error in 0%.
- **SC-004**: A driver failure reaches the caller as the framework's own error with the driver's error chained, in 100% of the cases the tests exercise, and the driver's own exception type reaches the caller in 0% of them.
- **SC-005**: The connection check appears exactly once in the driver — 1 occurrence — and `begin`, `commit`, `rollback` and each helper use it.
- **SC-006**: The proxy exposes no query member of either kind in 100% of cases, still refuses the lifecycle and context-manager use in 100% of cases, and still satisfies the contract — measured by the contract check on the proxy at one, two and three levels of wrapping.
- **SC-007**: A domain wrapper delegating one semantic method serves a nested action in 100% of the tests that exercise it, while the lifecycle stays refused.
- **SC-008**: The demo's suite passes with no database driver extra and no PostgreSQL running, and the number of tests needing a live database is 0; the demo's own read on a closed resource yields the framework's named failure rather than the base's own error.
- **SC-009**: Every example and notebook added or edited exits successfully with no live database, in 100% of cases.
- **SC-010**: The whole existing test suite passes, and the number of framework or adapter files edited for the removal — beyond the contract, the driver and the proxy themselves — is 0, verified by search rather than by assertion.
- **SC-011**: No public query member remains on any of the demo's stub resources, and the number of stub resources edited beyond removing the member and its import is 0.
- **SC-012**: Every helper added has a caller inside `packages/` — 0 helpers without one — measured by a search over the package sources, with the dead-code check green beside it (that check does not itself report an unused method at the confidence this repository runs it).
- **SC-013**: A search of the named pages for the removed member presented as the SQL query surface returns 0 occurrences, and the pages that teach querying name the helpers instead.
- **SC-014**: The changelog carries exactly one breaking-change entry naming the removal and both replacements, and the number of dated release headings and version bumps introduced by this feature is 0.
- **SC-015**: The new tests are red on the old code and green on the new code, in both directions recorded, and the adversarial break makes no other check fail; the break is restored afterwards.
- **SC-016**: The repository's own check run finishes green, and the two accepted remarks are the only ones in the log.
- **SC-017**: The number of places where a store without a database inspects the text of a statement to decide what to do is 0, measured by searching the demo for a statement-text test in a store.
- **SC-018**: The case that ran a query through the proxy is 0 — its script, notebook and tutorial section are gone — the nested-action case demonstrates a resource's own wrapper delegating its own semantic method while the lifecycle stays refused, and that case exits successfully with no live database, its printed output being the evidence.

## Assumptions

- The removal is a clean break: no compatibility shim, no deprecation window and no alias keeps the old member callable, because the obligation it imposes is the defect. The changelog is where a library user is told what replaced it.
- The framework and the adapters do not call the removed member today, so the code change is confined to the contract, the driver, the proxy, the demo's resources, the tests and the documentation. This was verified by search while writing this specification, and the search is a success criterion rather than an assumption about the future.
- The demo's identity domain, added by [#215](https://github.com/bystrovmaxim/aoa/issues/215), is the natural place to demonstrate the helpers, and it is already the resource a reader copies. Its driver-free base is what makes the two stores share one domain without a driver at import time.
- The two accepted remarks in the check log stay accepted, and nothing in this feature is expected to add a new one: the change touches no build configuration and no dependency.
- The pages and examples named here were located in the working tree while writing this specification; their line numbers have drifted since the issue was written, so planning re-locates each site before editing it.
