# Phase 0 — Research: The query surface leaves the SQL contract, and the driver keeps protected helpers

**Feature**: `specs/007-sql-contract-driver-helpers/spec.md` · **Branch**: `feature/issue-216-sql-contract-driver-helpers` · **Date**: 2026-10-17

Every decision below was taken against the working tree at the branch base `1e4c6b02`, not against the issue's
description of it. The issue was written before [#215](https://github.com/bystrovmaxim/aoa/issues/215) merged, so
wherever the two disagree the code wins and the difference is recorded.

## R1. What exactly leaves, and who called it?

**Decision**: the generic query member leaves four public places — the structural contract, the base resource, the
nested-action proxy and the driver — and the driver keeps the ability to run a statement under a protected name. The
eight demo stubs that override it lose the override and the `Any` import that existed only for it, and the demo's
in-memory identity store loses it too.

**Rationale**: measured by search, not assumed.

| Site | What it is today |
| --- | --- |
| `packages/aoa-action-machine/src/aoa/action_machine/resources/sql/protocol_sql_resource.py:76` | the structural member; the module docstring names it at `:12` and the AI-CORE `CONTRACT` key at `:43` |
| `.../resources/sql/sql_resource.py:148` | the abstract member; the contract line is at `:11` and the rollup walk-through calls it twice at `:52-53` |
| `.../resources/sql/wrapper_sql_resource.py:133-137` | the delegating member; the module docstring is at `:13` and the diagram at `:38` |
| `.../resources/postgres/postgres_resource.py:223-241` | the driver's implementation, which already holds the check and the wrap the helpers keep |

Callers, measured over `packages/*/src` and the adapters: **none**. Every hit for `execute(` outside the SQL contract
is either the driver's own `self._conn.execute("BEGIN" | "COMMIT" | "ROLLBACK")` (`postgres_resource.py:148`, `:169`,
`:184`, `:208`), an unrelated member of the runtime (`SagaCoordinator.execute`, `AspectExecutor.execute_regular`,
`execute_summary`, the MCP adapter's `_execute_tool_call`), or the demo's own `IdentityStoreBase.record_login`
(`identity_store_base.py:74`) — the single use of the removed member anywhere under `packages/`. In the tests, five
calls in `test_resource_unit_of_work.py` (`:80`, `:171`, `:172`, `:203`, `:252`) drive it as the way to do work, and
two test modules build doubles that implement or delegate it.

The demo's in-memory identity store is the sharpest evidence for the removal: because a generic member is the only
way that store can be written, it decides what to do by reading the statement text —
`identity_store_stub.py:69`: `if params and query.lstrip().upper().startswith("INSERT")`. A store with no SQL
parses SQL. That code disappears with the member.

**Alternatives considered**: (1) keep the member but stop obliging subclasses, by giving `SqlResource.execute` a
concrete harmless default — rejected, because a default that returns `"OK"` would let a stub claim to have written
what it never wrote, and the obligation, not the implementation, is the defect; (2) keep it only on the base and not
the protocol — rejected, because the fixtures that consume a resource are typed against the contract, and the point
is that nothing may call a passthrough through the framework's own type; (3) a deprecation alias for one release —
offered to the maintainer and rejected in the clarification session (clean break).

## R2. What do the four shapes become, member by member?

**Decision**: the after-state of each public shape is fixed here, and the docstrings, contract line, AI-CORE key and
diagrams move with it.

| Shape | Before | After |
| --- | --- | --- |
| `ProtocolSqlResource` | `rollup`, `open`, `begin`, `commit`, `rollback`, `close`, `execute` | the same members without `execute` |
| `SqlResource` | the same, with `open`/`begin`/`rollback`/`execute` abstract and `commit` concrete (rollup-aware) | `open`/`begin`/`rollback` abstract, `commit` concrete, `close` harmless, `rollup`, `check_rollup_support`, `get_wrapper_class` |
| `WrapperSqlResource` | refusals for `open`/`begin`/`commit`/`rollback`/`close`/`__aenter__`/`__aexit__`, `rollup`, `check_rollup_support`, `get_wrapper_class`, and a delegating `execute` | the same without the delegating member |
| `PostgresResource` | `open`, `begin`, `commit`, `rollback`, `close`, `execute` | `open`, `begin`, `commit`, `rollback`, `close`, `_execute`, `_fetchrow`, `_require_connection` |

**Rationale**: the four sites are the whole public surface of the query path, and each carries prose that names it —
the module docstrings of the protocol (`:12` "lifecycle + execution"), the base (`:11` "`open()`, `begin()`,
`commit()`, `rollback()`, `close()`, `execute()`"), the proxy (`:13` "allows query execution via `execute`") and the
driver (`:32` "| execute() -> SQL statement"). Leaving the prose behind would produce documentation that contradicts
the code in the four places a reader looks first, which the constitution's principle III exists to prevent.

**Alternatives considered**: (1) leave the docstrings to the documentation task — rejected, because principle III
makes the module header part of the change to the module, and the check run does not read prose; (2) rename the
member to `query` instead of removing it — rejected, because a renamed passthrough is the same obligation; (3) keep
`execute` on the driver alongside `_execute` for external users — rejected: that is the compatibility window the
maintainer refused.

## R3. The helpers: how many, of what shape, and where the check lives

**Decision**: exactly two — `_execute(query, params=None) -> str` and `_fetchrow(query, params=None) -> asyncpg.Record | None`
— both behind a single `_require_connection(self) -> asyncpg.Connection[asyncpg.Record]` that raises
`HandleError("Connection is not open")`. `begin`, `commit`, `rollback` and both helpers call it; the three lifecycle
failures keep their own wording. No `_fetch`, no `_fetchval`, no `executemany`.

**Rationale**: the check is written four times today (`postgres_resource.py`: `begin` at `:146`, `commit` at `:167`,
`rollback` at `:182`, and the member at `:238`), all four as the same two lines; one method is the single place the
spec's FR-006 asks for. The two shapes are the two the issue names, and each has a caller after this feature: the
statement helper through the demo's write path (`record_login`) and the row helper through its read path
(`read_person`). The row helper's parameters follow the removed member's own shape, `*params if params else ()`,
where a `None` and an empty tuple are the same thing.

Two measurements, taken while writing the clarification round, decide the shapes:

- **`fetchrow` costs nothing against `fetch`.** In the installed driver (asyncpg 0.31.0),
  `Connection.fetchrow` is `self._execute(query, args, 1, timeout, …)` and `Connection.fetch` is
  `self._execute(query, args, 0, …)` (`asyncpg/connection.py:666-760`); the limit travels as the protocol's Execute
  row cap, so no `LIMIT` is appended, the statement text is unchanged and the prepared-statement cache entry is the
  same. Its hazard is therefore semantic rather than performance: it answers the **first** row, so a query that can
  match several rows without an ordering silently yields an arbitrary one. The guidance says so, and the demo's read
  is keyed.
- **`vulture` does not police this, and the issue's premise that it does is wrong.** `pyproject.toml`
  (`[tool.vulture]`) sets `min_confidence = 80`, and an unused method carries 60 %: measured on a scratch file,
  `vulture --min-confidence 80` exits 0 on an unused private method, while `--min-confidence 60` reports
  `unused method '_unused_helper' (60% confidence)`. What the check does catch is an unused **import** (90 %) — which
  is exactly the `Any` the demo stubs lose. "No speculative API" is a rule the plan keeps because the maintainer
  chose it, not because a check would fail.

**Alternatives considered**: (1) `_execute` + `_fetchrow` + `_fetch`, with the demo keeping its multi-row read —
offered to the maintainer and rejected in favour of reshaping the read, which keeps the helper set at the two
members the issue names; (2) `_execute` + `_fetch` only — rejected because the issue names the row path as the read
shape and the guidance teaches it; (3) all four shapes including `_fetchval` and `executemany` — rejected as
speculation with no caller; (4) a helper that opens its own transaction — rejected, because the unit of work is the
resource's and a helper that opened one would hide the transaction from the domain that owns it.

## R4. The proxy after the shrink, `isinstance`, and how a domain gives nested access

**Decision**: `WrapperSqlResource` keeps every member it has except the delegating one, and stays the default the
base hands to nested actions. A domain that wants nested access overrides `get_wrapper_class()` with its own wrapper
class that delegates its own semantic methods.

**Rationale**: the framework builds the proxy in exactly one place — `ToolsBox._wrap_connections`
(`packages/aoa-action-machine/src/aoa/action_machine/runtime/tools_box.py:191`) calls
`connection.get_wrapper_class()` and constructs whatever class comes back — so the override is already the extension
point, and no new mechanism is needed. `SqlResource.get_wrapper_class()` (`sql_resource.py:117`) keeps returning
`WrapperSqlResource`; `WrapperSqlResource.get_wrapper_class()` returns itself (`:140`), which is what makes a second
and a third wrap behave as the first. The existing precedent is `OcelStoreWrapper`
(`packages/aoa-ocel/src/aoa/ocel/resource/ocel_store_wrapper.py`): it delegates `add_event` and refuses `open` and
`close`. The protocol is `@runtime_checkable` (`protocol_sql_resource.py:38`), and the proxy answers every member
that remains, so `isinstance(proxy, ProtocolSqlResource)` keeps holding — the member has to leave the protocol and
the proxy in the same change, and that is how the plan sequences it.

**Alternatives considered**: (1) give the proxy a re-export of the caller's semantic methods automatically, by
scanning the owner's public methods — rejected, because it would hand a nested action every public method of the
resource, including future ones, with no declaration; (2) keep a delegating `_execute` on the proxy and rely on the
"protected" prefix as the rule — rejected, because protection by naming is a convention, and the issue asks for
construction instead of a rule; (3) leave `get_wrapper_class()` returning `None` for SQL resources, so nothing is
wrapped — rejected, because the refusals and `rollup` propagation depend on the wrapper existing.

## R5. The demo without a database: where the primitives live, and what the read reshape costs

**Decision**: `IdentityStoreBase` declares `_read_person(person_id) -> dict[str, Any] | None` and
`_write_login(person_id, at) -> None`; `read_person` and `record_login` stay on the base and keep the transaction;
`IdentityStore` implements both primitives through `_fetchrow` and `_execute` and converts the driver's record into
a plain mapping; `IdentityStoreStub` implements both in memory and loses both the removed member and its
statement-text test.

**Rationale**: the base's own docstring states the split (`identity_store_base.py:11-16`: the domain states its two
operations and leaves the storage primitive to the implementation), so the change sharpens an existing decision
rather than inventing one. The maintainer confirmed the choice in the clarification round, with the sniffing code as
the decisive evidence.

The read reshape's blast radius, measured: `IdentityStoreBase.read_person` (`:63`), its AI-CORE `CONTRACT` key
(`:54`) and its diagram (`:30`); `IdentityStore._fetch_rows` (`:54-58`), which becomes the row primitive and drops
its own `RuntimeError` check for the helper's `HandleError`; `IdentityStoreStub._fetch_rows` (`:70-72`) and its
`people`/`logins` dictionaries; `IdentityLookupAction.identity_summary` (`identity_lookup.py:94-105`), where
`if not rows` becomes `is None` and `rows[0]` becomes the row itself; the demo's README and identity README; and
three test call sites in `packages/aoa-demo/tests/test_identity_postgres.py` (`:173`, `:204`, `:265`) plus the
collection assertion in `test_sql_resource_stubs.py`'s sibling test for the stub route (`rows == [PERSON]`). The
route's own two outcomes — the person or not — do not change.

**Alternatives considered**: (1) keep `read_person` returning a list and add `_fetch` to the driver — offered and
rejected (R3); (2) declare `read_person`/`record_login` abstract on the base and write each store's transaction —
offered and rejected, because the transaction would exist twice and the in-memory one would be ceremony;
(3) keep the in-memory store's statement sniffing and let it implement the driver's helpers — rejected: that is the
defect the feature removes, and it would put an asyncpg-shaped member back on a store with no driver; (4) drop the
in-memory store and let the demo need a database — rejected, because the demo's database-free mode is a property the
previous feature established and its suite depends on.

## R6. Which tests move, which are deleted, and what the new ones prove

**Decision**: one new test module for the helpers; four edited modules in the machine; two edited in the demo; one
edited test-support module. One test is deleted (the "subclass missing `execute` cannot be instantiated" case) and
one test class is replaced (the proxy's delegation cases).

**Rationale**:

| Test site | Today | After |
| --- | --- | --- |
| `tests/support/fake_pool.py:69-101` | `FakeConnection` answers `execute` and `close` | also answers `fetchrow`, recording the statement and the parameters, returning one row or `None` |
| `tests/action_machine/resources/test_sql_resource.py:59-110` | two doubles implement the member and record statements | the member is gone; the doubles keep `open`/`begin`/`rollback`/`commit` |
| `.../test_sql_resource.py:220-283` | four incomplete-subclass cases, one per abstract member | three (`open`, `begin`, `rollback`); the `execute` case is deleted, because a member that is not in the contract cannot be missing from a subclass |
| `.../test_sql_resource.py:299-345` | the lifecycle cases call the member to represent work | the lifecycle cases drive `begin`/`commit`/`rollback` and rollup; a guard asserts the contract exposes no query member |
| `.../test_wrapper_sql_resource.py:95` and `:109` | the mock manager exposes `execute` as an `AsyncMock` and the double implements it | the member disappears from both, and the delegation tests are replaced by absence tests (`hasattr` false for `execute`, `_execute`, `_fetchrow`) |
| `.../test_wrapper_sql_resource.py:272-300` | three delegation cases (delegates, forwards parameters, wraps the error) | deleted; the error-wrapping case is re-expressed against a domain wrapper's own delegated method |
| `.../tests/action_machine/resources/__init__.py:19`, `:38` | the contract note and the module map name the member | corrected |
| `.../test_resource_unit_of_work.py:80,171,172,203,252` | five calls of the removed member | `_execute` — the test is the driver's subclass, and pylint's protected-access rule is off for tests |
| `packages/aoa-demo/tests/test_identity_postgres.py` | asserts a list of rows and calls the read on a closed resource | asserts one row or `None`, and the closed-resource failure is now the framework's `HandleError` |

**Alternatives considered**: (1) keep the delegation tests by giving the mock manager a `_execute` and asserting the
proxy forwards it — rejected: the proxy must not forward anything, and a test that asserts forwarding would pin the
behaviour the feature deletes; (2) test "the check appears once" by reading the module source in a test — rejected as
a brittle test; the source search belongs to the closing task's `grep` evidence (SC-005).

## R7. The documentation and example inventory, verified site by site

**Decision**: the pages and scripts the issue names are edited as the plan's Documentation design table states, and
the pages that keep their own `execute` for their own reasons are listed as deliberately untouched.

**Rationale**: the sites below were located in the working tree after #215 rewrote the PostgreSQL page, so the
issue's line numbers are not used.

| Site | Evidence |
| --- | --- |
| `docs/extensions/postgresql.md` | `:35` describes the member as the query surface; `:650` says the proxy delegates it; `:73`, `:207`, `:400`, `:432`, `:467`, `:609-614` show it in use, including a custom resource overriding it |
| `docs/extensions/postgresql.ru_draft.md` | the same sites in Russian; the draft exists and is updated with the page |
| `docs/how-to/authoring-resource.md` | `:118` says the wrapper delegates the member; the page is where the helpers must be taught |
| `docs/how-to/choosing-action-aspect-resource.md` | `:50` says the wrapper may execute permitted commands |
| `docs/tutorials/step-19-resource.md` | `:225` is the section to delete; `:209` and `:324` are the neighbouring sections that absorb the claim and the domain wrapper |
| `docs/tutorials/step-19-resource.ru_draft.md` | `:225` and the surrounding sections in Russian |
| Root `README.md` | `:604-618` teaches a resource calling the member on the driver |
| `examples/extensions/postgresql/*` | `02_concurrent.py:80`, `04_commit.py:70`, `05_rollback.py:72`, `07_rollup.py:70`, `14_failed_commit.py:73` (the last overriding the member) |
| `examples/step_17_connections/16_pool_lifespan.py:99` | calls the member on the declared connection |
| `examples/step_19_resource/04_wrapper_execute.py` + `.ipynb` | the case to delete, with `docs/tutorials/step-19-resource.md`'s link to it |
| `examples/step_19_resource/07_nested_action.py:99` | the nested case calls the member; it is also where the domain wrapper is demonstrated afterwards |
| `docs/how-to/migrating-legacy.md:42` | pre-AOA code — checked, not assumed |
| Untouched: `docs/how-to/authoring-resource.md`'s ledger example, `examples/how_to/06_custom_resource.py`, `examples/step_06_dependencies/01_depends.py`, `docs/tutorials/step-06-dependencies.md`, `packages/aoa-ocel/**` | each `execute` belongs to a resource's own semantics, not to the SQL contract (FR-024) |

The examples runner (`tests/examples/test_examples_run.py`) discovers scripts by walking `examples/**/*.py`, so
deleting one needs no manifest change; the later cases keep their numbers, and the gap is recorded as an edge case
in the specification.

**Alternatives considered**: (1) renumber the tutorial cases after the deletion — rejected: it renames every later
notebook and rewrites every link for no reader benefit; (2) move the deleted case's content into the PostgreSQL page
instead of the nested-action case — rejected, because the nested case is where the runtime supplies the proxy and so
where the pattern is actually visible.

## R8. The release question, and what the stale-fragment sweep looks for

**Decision**: the article goes under `## [Unreleased]` in `packages/aoa-action-machine/CHANGELOG.md` with a
`### Breaking changes` section; the demo's changelog gains its own short breaking-change entries; no dated heading
and no version bump are introduced; `docs/CHANGELOG.md` is untouched.

**Rationale**: the maintainer settled this in the clarification session, on the precedent recorded while #215 was
written: `pyproject.toml` says `1.0.1a3`, the changelog's last release is `1.0.1a2` plus `## [Unreleased]`, and the
release commit `948a2e66` raised versions without touching a changelog — so a version in metadata names the version
under development, and the dated heading is the maintainer's release act.

The sweep the closing task runs, over the branch base `1e4c6b02`, looks for four things and records the count of
each: a public query member on a SQL resource; a call of the removed member anywhere under `packages/`; a page that
presents it as the SQL query surface (the four pages named in the plan, plus the example scripts); and a store that
decides what to do from statement text (SC-017). Each search is run against the branch base as well as the tip, so
that "0 today" is a difference and not an assumption.

**Alternatives considered**: (1) a dated entry and a version bump as the issue words it — offered and rejected;
(2) a `docs/CHANGELOG.md` article as well — rejected for this size of change, with the maintainer free to ask for
one; (3) writing the changelog alongside the code — rejected by principle VI, which makes it the last step.

## R9. What this plan deliberately does not resolve

- The changelog's prose: written at the closing task, from the finished code, as one article.
- Whether the maintainer wants a `docs/CHANGELOG.md` article for a change of this size (R8 records the default).
- Whether the root `README.md` needs a Russian draft — it has none today, and none is invented for an edited section.
- The final wording of the helpers' docstrings, beyond "one line, purpose stated, identifiers in double backticks".
- An observation that is out of scope and left alone: `packages/aoa-action-machine/src/aoa/action_machine/exceptions/__init__.py`
  lists `"HandleError"` twice in `__all__` (`:104-105`). It is a real defect in a file this feature does not need to
  touch, so it is recorded here rather than fixed silently.
