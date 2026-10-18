# Feature Specification: A domain reads all rows and one value through the driver's protected helpers

**Feature Branch**: `feature/issue-222-fetch-helpers`

**Created**: 2026-10-18

**Status**: Draft

**Input**: User description: "https://github.com/bystrovmaxim/aoa/issues/222 — the protected helpers cover two of the driver's four answers, a write (`_execute`) and a first row (`_fetchrow`). A domain that needs all rows or one value still reaches for `self._conn`. The gap was found by a consumer outside this repository, bystrovmaxim/gameoffer#72."

## Clarifications

### Session 2026-10-18

- Decision carried over from the issue: **the pair is added now, and this supersedes the previous specification's decision not to add it.** The clarification session of [#216](https://github.com/bystrovmaxim/aoa/issues/216), recorded in `specs/007-sql-contract-driver-helpers/spec.md`, chose exactly two helpers and explicitly left `_fetch` and `_fetchval` out, on the ground that no domain method in the repository read several rows or a single value, and that a helper appears only when a caller does. A consumer outside this repository has since found the gap — bystrovmaxim/gameoffer#72 — and the demo's own PostgreSQL store gains the two private reads that call them, so both conditions the earlier decision asked for now hold. The earlier decision is not wrong; its premise changed.
- Decision carried over from the issue: **the set of helpers closes at four.** `_execute`, `_fetchrow`, `_fetch`, `_fetchval` — one per driver answer — and no convenience member beside them. `_fetchmany`, `_executemany`, `_fetchval_or`, `_fetchrow_or` and the like do not appear: a domain that wants a default composes it from the four.
- Decision carried over from the issue: **the public and protected contract of the SQL resource does not grow.** `ProtocolSqlResource`, `SqlResource` and `WrapperSqlResource` stay exactly as in 1.0.1a4, with no query member added. The helpers live on `PostgresResource` alone, so a nested action — which receives the wrapper — still cannot reach a query surface at all, by construction rather than by a refusal.
- Decision taken while writing this specification: **named parameters are refused by the annotated signature, not by a runtime guard.** `params` is a tuple of positional values; a `dict` is outside the contract, and the pair adds no `isinstance` check, for two reasons. The issue closes the message set at two (FR-006), so a guard would have no text of its own to raise; and `_execute` and `_fetchrow` carry the same annotation with no guard, so a guard on the new pair alone would make four helpers behave in two shapes. What the contract says is that a `dict` is not an accepted parameter; what happens at runtime is the same thing that happens to the existing pair today — unpacking yields the keys as positional values and the driver's complaint arrives wrapped as `HandleError`. Documented as a boundary of the contract rather than repaired in it.
- Decision taken while writing this specification: **`_fetchval` cannot tell "no row" from "a row whose first value is NULL".** The driver's `fetchval` answers `None` in both cases, and the helper inherits that. Nothing is invented to separate them: the docstring and the pages say it plainly, and a domain that must know which of the two it saw uses `_fetchrow` and checks the row. Adding a sentinel or an `_fetchval_or` would be the speculative member the previous decision — and the issue — refuse.
- Decision taken while writing this specification: **the demo's PostgreSQL store gains two private storage reads and nothing else changes there.** The issue asks the demo domain to call both helpers in its own methods: a page through `_fetch`, a count through `_fetchval`. The store therefore gains one private read that lists a bounded, ordered page of people and one that answers the count, and the demo's suite is what calls them. The driver-free base and the in-memory store are untouched — they keep the two operations they have — and no public operation, action, route or MCP tool is added: this is a demonstration of the helpers, not a listing screen, and the maintainer confirmed in the clarification session that the demo is a shell for the graph rather than a surface to grow.
- Decision taken while writing this specification: **`vulture` is green by itself, and the real evidence is the caller, not the check.** Measured for #007: the repository runs `vulture` at `min_confidence = 80`, while an unused method carries 60 % confidence, so an uncalled helper would not fail the check run. The issue's NFR-3 and AC-6 therefore cannot be satisfied by passing `vulture` — they are satisfied by the demo's callers and by the search that shows them. The confidence threshold is not lowered and no fake caller is added to please a check.
- Decision taken while writing this specification: **sites are named by member and by page, not by line number.** The line numbers the issue cites have already drifted once, and #007 recorded the same correction. Planning re-locates every site before editing it.
- Decision taken while writing this specification: **the changelog entry goes under `## [Unreleased]`, with no dated heading and no version bump.** The issue lists "version and journal entry" in scope and asks for an additive change on 1.0.1a4. In [#215](https://github.com/bystrovmaxim/aoa/issues/215) the maintainer corrected exactly that reading: a version in package metadata names the version under development, and the dated heading is the maintainer's release act. The article is therefore an `### Added` entry under `## [Unreleased]` in `packages/aoa-action-machine/CHANGELOG.md`; no `### Breaking changes` section, because nothing is removed. One word from the maintainer overturns this.
- Decision taken while writing this specification: **the specification uses the library's own vocabulary** — contract, resource, driver, helper, wrapper, nested action, unit of work — because this feature *is* that vocabulary. Clarification markers are therefore used only where the issue leaves a decision genuinely open; today there are none.

### Session 2026-10-18 — clarification

- Q: Where exactly should the demo call the two new helpers — through new public domain operations, through an action and an HTTP route, or through private storage methods? → A: **Through two private storage methods on the demo's PostgreSQL store, with the demo's suite as their caller.** No public domain operation, action, route or MCP tool is added; the driver-free base and the in-memory store are unchanged. The maintainer's wording: the demo is a shell for building the graph, and the private methods are for internal use. FR-015 … FR-020 and US4 stand as rewritten.
- Q: How should the helpers treat a mapping of named parameters instead of a tuple? → A: **By the same principles as `_execute` and `_fetchrow`** — the parameter is an annotated positional tuple, a mapping is outside the contract, and no runtime guard and no third message are added. FR-007 and the decision bullet above stand as written.
- Q: Does the change carry a version bump and a dated changelog heading, as the issue's wording literally asks? → A: **No — one `### Added` article under `## [Unreleased]`, no version bump and no dated heading.** The maintainer confirmed the #215 reading over the issue's wording. FR-023 stands as written.

### Session 2026-10-18 — after planning

- Decision taken while turning the plan into tasks: **the pages' worked example ships as a script and a notebook as well.** Principle VI of the constitution requires every case the change introduces to appear twice — a runnable script under `examples/` and a notebook of the same case — and says that documentation which does not execute is a claim. The case is therefore `examples/extensions/postgresql/15_fetch_and_fetchval.py` with its `.ipynb`, executed by `tests/examples`, and the page's example is what the script prints. Added as FR-025 and SC-013; the plan's documentation design and scale carry it, and tasks T017 and T018 write and run it.

## User Scenarios & Testing *(mandatory)*

The readers of this feature are a developer writing a domain resource that lists rows, a developer whose method needs one number, the reader of the demo, and the library user on 1.0.1a4 who upgrades.

### User Story 1 - A domain answers a page of rows without reaching for the connection (Priority: P1)

A developer writes a semantic method on a resource over PostgreSQL that answers a collection — the offers of a person, the people in a page. The method calls one protected helper and gets every row the driver answered, in the driver's order, with an empty list when nothing matched. It never sees the connection, never writes the "is it open" check, and never wraps a driver failure by hand.

**Why this priority**: this is the reason a consumer outside the repository reopened the subject. Without it, the only way to answer a collection is to call a first-row helper in a loop and lose every row after the first, or to reach past the helper into the connection — the exact reach-through the helpers exist to remove.

**Independent Test**: call the helper on a resource whose connection answers three rows and confirm the method receives all three in order; call it with no match and confirm an empty list rather than nothing; call it on a resource that never opened and confirm the named failure.

**Acceptance Scenarios**:

1. **Given** an open resource whose connection answers several rows, **When** the method calls the helper, **Then** it receives every row in the driver's order — with an `ORDER BY` in the statement and without one.
2. **Given** the same resource and a statement that matches nothing, **When** the helper is called, **Then** the answer is an empty list, not nothing.
3. **Given** a statement that matches one row, **When** the helper is called, **Then** the answer is a list holding that row, not the row itself.
4. **Given** a resource that never opened, **When** the helper is called, **Then** the failure is the framework's named failure, and nothing reaches the connection.

---

### User Story 2 - A domain answers one value without unwrapping a row (Priority: P2)

A developer needs one number — `count(*)`, an id, a flag — and calls a helper that answers the first value of the first row. The answer is the value, not a record and not a tuple, and nothing matched answers nothing. The method does not fetch a row to read one column out of it, and it does not reach for the connection.

**Why this priority**: the count path is the second half of the gap the consumer found. It is smaller than the page path, but it is the one whose absence is most visible in a page that guards an empty state, because a count is what tells a caller whether there is a next page at all.

**Independent Test**: call the helper against a statement answering one row and confirm the scalar rather than the row; call it with no match and confirm nothing; make the driver refuse and confirm the wrapped failure.

**Acceptance Scenarios**:

1. **Given** an open resource and a statement that matches a row, **When** the helper is called, **Then** the answer is the first value of the first row — not the row, not a tuple, not the string rendering of either.
2. **Given** the same resource and a statement that matches nothing, **When** the helper is called, **Then** the answer is nothing.
3. **Given** a row whose first value is a SQL `NULL`, **When** the helper is called, **Then** the answer is nothing as well, and the caller is told — by the docstring and the pages — that the two cases are not distinguishable through this helper.
4. **Given** a resource that never opened, **When** the helper is called, **Then** the failure is the framework's named failure.

---

### User Story 3 - The pair behaves exactly like the helpers it joins (Priority: P3)

A developer who has learned the two existing helpers learns nothing new: the new pair asks for the connection through the one function that checks it, names a closed resource with the one message the framework already uses, turns any driver failure into the framework's error with the driver's error chained, takes positional parameters the same way, and answers a plain annotation that carries no driver type. A method that wants its own context catches that error precisely as before.

**Why this priority**: a second policy for the same job would be worse than the missing helper, because every domain method would then have to know which of the four answers in which shape. It ranks below the two helpers themselves because it is about the shape they must have rather than the capability they add.

**Independent Test**: exercise both new helpers through every path the existing pair is checked on — closed resource, driver failure, parameters, annotation — and confirm the same two messages, the same chaining and the same call shape; confirm the existing pair's checks pass unchanged.

**Acceptance Scenarios**:

1. **Given** a resource that never opened, **When** either new helper is called, **Then** the failure is the named closed-connection failure, and no failure to read a missing attribute arrives instead.
2. **Given** a resource closed after opening, **When** either new helper is called, **Then** the same named failure arrives.
3. **Given** an open resource whose connection refuses the statement, **When** either new helper is called, **Then** the framework's error arrives with the driver's error chained as its cause.
4. **Given** a call with no parameters and a call with an empty tuple, **When** the connection is inspected, **Then** it saw the same call both times, with no arguments.
5. **Given** the return annotation of the page helper, **When** it is read, **Then** it names a list of plain values and no driver type appears in it.
6. **Given** the four query helpers on the driver, **When** they are listed, **Then** there are exactly four and no convenience member beside them.

---

### User Story 4 - The demo's store calls both helpers in its own private reads (Priority: P4)

A reader opens the demo's PostgreSQL store and finds the new pair already in use: one private read asks the database for a bounded, ordered page of people through the page helper and answers plain mappings; another asks for the count through the value helper and answers a number. The driver-free base and the in-memory store are untouched, so the demo still runs with no database and no driver extra, and the suite runs both reads over the faked pool.

**Why this priority**: the demo is how the pattern is copied rather than reconstructed, and it is what gives each new helper a caller inside `packages/` — the condition the previous specification set for adding them. It ranks below the helpers themselves because it demonstrates them, and it stays at two private reads because the maintainer chose the smallest demonstration that satisfies the rule.

**Independent Test**: read the demo's PostgreSQL store and confirm the two private reads call the page helper and the value helper and never touch the connection; read the base and the in-memory store and confirm neither grew a page or a count; run the demo suite with no database and confirm both reads pass.

**Acceptance Scenarios**:

1. **Given** the demo's PostgreSQL store, **When** its private reads are listed, **Then** one goes through the page helper and one through the value helper, and neither uses the connection directly.
2. **Given** the page read, **When** it answers, **Then** it answers plain mappings rather than driver records, with a deterministic order and a bounded page stated in its own statement.
3. **Given** the count read, **When** it answers, **Then** it answers a plain number, and its statement asks the database for one value rather than for a row.
4. **Given** the demo's driver-free base and in-memory store, **When** they are read, **Then** neither gained a page or a count, and the demo still imports and runs with no database and no extra installed.
5. **Given** the demo's package documentation and the store's own architectural diagram, **When** they describe what the store does, **Then** the two new reads and the helpers behind them are named beside the existing pair.

---

### User Story 5 - The contract stays where it was, so a 1.0.1a4 consumer needs no edit (Priority: P5)

A library user on 1.0.1a4 upgrades and changes nothing: their SQL resource subclasses, their wrappers and their nested actions compile and run as before, because nothing was removed and no member was added to a contract they implement or inherit. The four helpers are documented as the extension point, with a page and a count as the worked example, so the next domain method starts from the pattern rather than from the connection.

**Why this priority**: the change is additive by the issue's own constraint, and documentation ships with the change. It ranks last because it follows from doing the other four correctly, and because a wrong statement here would be a promise the code does not keep.

**Independent Test**: read the three contract modules and confirm no query member appears in them; run the existing suites without editing a test and confirm they pass; read the two documentation pages and confirm all four helpers are listed with a page example and a count example.

**Acceptance Scenarios**:

1. **Given** the structural contract, the base resource and the wrapper, **When** their members are listed, **Then** none of them carries a public or protected query member, exactly as in 1.0.1a4.
2. **Given** the existing suites, **When** they run without an edit, **Then** they pass, and no existing check changed meaning.
3. **Given** the package's changelog, **When** the entry is read, **Then** it sits under the unreleased heading, says in plain words what a domain can now do, and claims no breaking change.
4. **Given** the PostgreSQL page and the authoring page, **When** the helper section is read, **Then** all four helpers are listed, and one example shows a page through the page helper and a count through the value helper.

---

### Edge Cases

- **A single row.** The page helper answers a list of one; a caller that wants the row itself uses the row helper. The count helper answers the value, never a row.
- **No match.** The page helper answers an empty list, the value helper answers nothing — the same answer a matched row with a SQL `NULL` in its first column gives. The distinction is unavailable through the value helper by design, and is stated wherever the helper is documented.
- **Several rows without an ordering.** The answer is every row, in whatever order the driver produced; the helper neither adds nor promises an ordering. The demo's page states its own order so that a page is stable across calls.
- **A closed resource, and one that never opened.** Both are the named closed-connection failure. A failure to read a missing attribute must not arrive instead.
- **A driver failure.** It arrives as the framework's error with the driver's error chained; a method that wants its own message catches that error and raises its own with the cause attached, as with the existing pair.
- **Named parameters.** A `dict` is outside the annotated contract; the helpers add no runtime guard and no third message, so what a caller gets is the driver's own complaint, wrapped. Documented as a boundary, not repaired.
- **Cancellation.** As with the existing pair, a cancelled unit of work is not a driver failure and is not turned into the framework's error; the transaction cleanup that already exists does not change.
- **A nested action.** It receives the wrapper, which carries no query member at all, so the new pair is not reachable from it — not even as an inherited protected member, because the wrapper does not inherit from `PostgresResource`.
- **A page requested past the last row.** The page helper answers an empty list, exactly as it does for no match; paging is the caller's arithmetic, and the count helper is what a caller uses to know where the end is.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The driver MUST offer a protected helper for all rows: it takes a query string and an optional tuple of positional parameters, and answers every row the driver returned, in the driver's order.
- **FR-002**: The page helper MUST answer an empty list when the statement matched nothing, and MUST NOT answer nothing.
- **FR-003**: The driver MUST offer a protected helper for one value: it takes a query string and an optional tuple of positional parameters, and answers the first value of the first row.
- **FR-004**: The value helper MUST answer nothing when the statement matched nothing, and MUST NOT answer a row, a tuple or a rendering of either.
- **FR-005**: Both new helpers MUST take their connection only through the one function that checks it, and MUST refuse a resource that is not open with the framework's named closed-connection failure. A failure to read a missing attribute MUST NOT be raised.
- **FR-006**: Any failure of the driver inside either helper MUST arrive as the framework's own error, carrying the driver's error as its cause. Neither helper introduces message text other than the two messages the existing pair already uses.
- **FR-007**: Parameters MUST be positional, as in the existing pair. No parameters and an empty tuple MUST produce the same call to the driver, with no arguments. A mapping of named parameters MUST NOT be an accepted parameter.
- **FR-008**: The page helper's return annotation MUST name a list of plain values, and no driver type MUST appear in a signature the domain can see — the same ground on which the row helper answers a plain value.
- **FR-009**: The four protected query members MUST remain exactly four: a statement, a first row, all rows, one value. No further query helper MUST appear beside them.
- **FR-010**: Both helpers MUST carry docstrings in the existing style — purpose, arguments, return, Raises — because they are the extension point. The page helper's docstring MUST say that it answers every row in the driver's order with an empty list for no match; the value helper's MUST say that it answers the first value of the first row and that no match and a SQL `NULL` are indistinguishable through it.
- **FR-011**: The module documentation of the driver MUST name all four query helpers where it describes the resource's data flow and its contract, so the listing a reader skims is not one helper short.
- **FR-012**: The documentation of the statement helper, which today sends a row-reading subclass to the row helper alone, MUST name both read helpers so that the choice between them is visible where a reader is already looking.
- **FR-013**: The SQL contract, the base resource and the wrapper MUST be unchanged: no public or protected query member is added to any of them, and the wrapper MUST NOT expose the new pair in any form.
- **FR-014**: The existing statement and row helpers, the connection check and the lifecycle members MUST NOT change behaviour; no existing check changes meaning.
- **FR-015**: The demo's PostgreSQL store MUST gain two private storage reads — one answering a bounded, ordered list of people and one answering the count of people — so that both new helpers have a caller inside `packages/`.
- **FR-016**: The list read MUST reach the database through the page helper and MUST answer plain mappings rather than driver records; the count read MUST reach the database through the value helper and MUST answer a plain number.
- **FR-017**: The list read MUST state a deterministic order and a bounded page in its own statement, so that the example teaches an ordering rather than leaving it to the driver.
- **FR-018**: The demo's driver-free base and its in-memory store MUST NOT change: they keep the two operations they have, and no page or count is added to them.
- **FR-019**: The demo's suite MUST exercise both new reads over the faked pool, and the faked connection MUST answer the driver calls the two helpers make, so that each read is shown to run through its helper rather than beside it.
- **FR-020**: The demo's description of its PostgreSQL store — the package documentation and the store's own architectural diagram — MUST name the two new reads and the helpers behind them, beside the existing pair.
- **FR-021**: The PostgreSQL page in `docs/extensions/postgresql.md` and the authoring page in `docs/how-to/authoring-resource.md` MUST list all four helpers, and MUST show one example: a page through the page helper and a count through the value helper, with the count's answer handled as a value rather than as a row.
- **FR-022**: The Russian counterparts of those pages, which live beside them as drafts and do not enter a commit, MUST carry the same four helpers and the same example.
- **FR-023**: The package's changelog MUST gain one article under the unreleased heading describing what a domain can now do, with no breaking-change section and no dated release heading.
- **FR-024**: No live database MUST be required by any check this feature adds or changes.
- **FR-025**: The documentation MUST ship the page-and-count case as a runnable script under `examples/` and as a notebook of the same case, both executed with the repository's own environment while they are written — the constitution's rule that every case appears twice and that documentation which does not execute is a claim (Principle VI, points 5 and 6).

### Key Entities

- **Protected query helper**: a member of the driver that a subclass calls, one per driver answer. Four exist after this feature — a statement, a first row, all rows, one value. It owns the connection check and the wrapping of a driver failure; a domain method owns the business meaning.
- **Driver answer**: what the database returns for one call. A page helper returns all rows; a value helper returns the first value of the first row. The two are the answers the existing pair does not cover.
- **SQL contract**: the structural contract, the base resource and the wrapper. It names a lifecycle and no query member, and this feature does not change it.
- **Demo storage read**: a private method on the demo's PostgreSQL store that reaches storage through a helper and answers a domain-shaped result. The store already had a read and a write; this feature adds the list read and the count read, and the suite is their caller.
- **Documentation entry**: a listing of the four helpers and a worked example of a page and a count, present on the PostgreSQL page and the authoring page and in their draft counterparts.

### Out of scope

- Any public query member in the structural contract, the base resource or the wrapper. Adding one would undo [#216](https://github.com/bystrovmaxim/aoa/issues/216).
- `executemany`, cursors, bulk copy, query timeouts, a record class, pool bounds and transactional helpers. The four helpers are the whole surface this feature adds.
- Any change to the statement helper, the row helper, the connection check, or the lifecycle members.
- Any behaviour change in the wrapper: no member of it is added, removed or re-delegated.
- An action, route, MCP tool, screen or public domain operation for the demo's new reads, and any change to the demo's driver-free base or its in-memory store. The issue asks the demo to demonstrate the helpers; the maintainer chose two private reads on the PostgreSQL store, with the suite as their caller.
- A migration or a schema change for the demo: both reads query a table the domain already reads, and the repository carries no schema definition for it.
- A dated release heading or a version bump; that is the maintainer's release act, as recorded in [#215](https://github.com/bystrovmaxim/aoa/issues/215) and in the previous specification.
- Rewriting unrelated documentation, tutorials or examples that mention the helpers in passing.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On a statement matching several rows, the page helper answers exactly those rows in the driver's order — verified both with an `ORDER BY` and without one — and on a statement matching nothing it answers an empty list.
- **SC-002**: On a statement matching a row, the value helper answers the first value of the first row and not the row or a tuple; on a statement matching nothing it answers nothing.
- **SC-003**: On a resource that never opened and on one closed after opening, both helpers answer the framework's named closed-connection failure, and no missing-attribute failure is raised in either case.
- **SC-004**: When the driver refuses, both helpers answer the framework's error with the driver's error as its cause.
- **SC-005**: A call with no parameters and a call with an empty tuple reach the connection identically, and a call without parameters carries no arguments into it.
- **SC-006**: A listing of the driver's query helpers shows exactly four, and a search of the contract, the base resource and the wrapper shows no query member added by this feature.
- **SC-007**: A search of the demo's PostgreSQL store shows the list read calling the page helper and the count read calling the value helper, and shows no direct use of the connection in either.
- **SC-008**: The demo's suite passes with no database and no database extra installed, and covers both new reads over the faked pool; the driver-free base and the in-memory store carry no page and no count.
- **SC-009**: The dead-code check is green, and both new helpers have a caller under `packages/` — the caller being the evidence, since the check's confidence threshold does not report an uncalled method.
- **SC-010**: Both documentation pages, and their draft counterparts, list all four helpers and contain the page-and-count example.
- **SC-011**: The suites of both packages pass without a live database, with no existing check edited to accommodate the new pair.
- **SC-012**: An SQL resource subclass that was valid on 1.0.1a4 is still valid after the change: it implements the same members, publishes no query member, and its existing checks pass unedited.
- **SC-013**: The page-and-count case exists as both a script and a notebook, the script exits zero with no database, and the examples runner passes.

## Assumptions

- The domain the issue names is the identity domain added by [#215](https://github.com/bystrovmaxim/aoa/issues/215), under `packages/aoa-demo/src/aoa/demo/model/identity`.
- The driver's own answers are four in number — a status, a first row, all rows, a first value — and the four helpers map onto them one to one. The value helper is available on the driver versions the package already supports, and the row helper's use of it is a matter of shape rather than of capability.
- Both new queries read tables the demo's PostgreSQL store already queries — the person table for the page and for the count — so no schema definition, no migration and no seeded data are added. What a real database holds is outside the suite, which uses a faked connection.
- The demonstration lives in the demo's suite: two private reads on the PostgreSQL store, with the driver-free base and the in-memory store left as they are, because the maintainer chose the smallest demonstration and the issue's requirement is that the domain's own methods call both helpers.
- The package's existing test modules and their contract docstring keep their structure; the new checks sit beside the existing pair's checks in the same module.
- The documentation pages carry a Russian draft beside them, and the served English page is the one that enters a commit.
- `vulture` runs as the repository configures it, at a confidence threshold that does not report an unused method; passing it is necessary and not sufficient, and the caller under `packages/` is what shows the rule was kept.
- No version bump and no dated release heading are produced by this feature; the unreleased article is what a later release carries.
