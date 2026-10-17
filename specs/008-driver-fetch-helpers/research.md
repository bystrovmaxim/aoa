# Phase 0 — Research: A domain reads all rows and one value through the driver's protected helpers

**Feature**: `specs/008-driver-fetch-helpers/spec.md` · **Date**: 2026-10-18

Every point below is a decision the design needs, with what was measured or read to settle it. The driver's source
was read from the installed package (`asyncpg` 0.31.0, the `postgres` extra of `aoa-action-machine`), and each test
figure comes from a run on this branch before the change.

## R1. The two helpers are thin delegations, and the driver already answers what they promise

**Decision**: `_fetch` delegates to `asyncpg.Connection.fetch` and returns its list unchanged; `_fetchval` delegates
to `asyncpg.Connection.fetchval` and returns its value unchanged. No `LIMIT` is appended, no row is converted, no
loop or second query is introduced.

**Rationale**: read from the installed driver. `fetch(query, *args, timeout=None, record_class=None)` answers a
`list` of records and passes a row cap of `0`, meaning every row. `fetchval(query, *args, column=0, timeout=None)`
answers the value of the given column of the first record, and explicitly answers `None` when no records came back —
which is the spec's "no match answers nothing" and its "no row and SQL `NULL` are indistinguishable" edge case, both
inherited from the driver rather than invented here.

**Alternatives considered**: a loop over `_fetchrow` — rejected, it loses rows and multiplies round trips; a
`_fetch` that slices for a page — rejected, paging is the caller's arithmetic and the helper promises every row;
`_fetchval` built on `fetchrow` plus a column read — rejected, it is the same driver call with more code in the
helper and the same `None` ambiguity.

## R2. The return annotation is `list[Any]`, and the module keeps lazy annotations

**Decision**: `_fetch` is annotated `list[Any]`, not `list[asyncpg.Record]`; `_fetchval` is annotated `Any`, as
`_fetchrow` already is.

**Rationale**: the spec's FR-008 makes the driver's type a thing the domain must not see. `PostgresResource` already
carries `from __future__ import annotations`, so these annotations stay strings at import time — the same mechanism
that makes the existing `asyncpg.Connection[asyncpg.Record]` annotation on `_require_connection` legal even though
the class is not subscriptable at runtime.

**Alternatives considered**: the exact driver type, which would leak the driver into a domain-facing signature and
make a test double harder to type; a generic parameter on the class, which is a contract change the spec forbids.

## R3. Named parameters stay outside the contract, with no runtime guard

**Decision**: `params` stays `tuple[Any, ...] | None`, the call stays `*params if params else ()`, and no
`isinstance` check is added. A `dict` is refused by the annotation alone.

**Rationale**: the spec's clarification answer (the maintainer: "the same principles as `_execute` and
`_fetchrow`"). A guard would need a third message, and the issue closes the message set at two; it would also make
four helpers behave in two shapes. At runtime a mapping's keys would unpack as positional values and the driver's
complaint arrives wrapped as `HandleError`, exactly what happens to the existing pair today.

**Alternatives considered**: raising `TypeError` before the driver — rejected as a new failure shape beside the two
the helper set has; accepting mappings and forwarding them — rejected by the issue's FR-5.

## R4. `vulture` is green by itself; the caller is the evidence

**Decision**: no threshold change, no `# noqa`, no fake caller. The evidence for "each helper has a caller" is the
demo's private reads plus the search over `packages/*/src`.

**Rationale**: `pyproject.toml` sets `[tool.vulture] min_confidence = 80`, and an unused method is reported at 60 %,
so an uncalled helper would not fail the check. Measured while #007 was written and unchanged today. What the check
does catch is an unused import, and this feature adds none — the module already imports `Any`.

**Alternatives considered**: lowering `min_confidence` to 60 — rejected, it would surface the repository's existing
unused-member debt across eight packages; annotations on the new members to silence a check that does not fire.

## R5. The fakes gain the two driver calls, so every check stays database-free

**Decision**: `FakeConnection` (in `packages/aoa-action-machine/tests/support/fake_pool.py`) gains `rows` and `value`
plus the two async methods `fetch` and `fetchval`, both recording `(query, args)` through the existing `_operate`
guard. The demo's `_FakeConnection` (in `packages/aoa-demo/tests/test_identity_postgres.py`) gains the same two
methods and a seeded list of person records.

**Rationale**: both fakes are the repository's instrument for "the driver without a database"; adding the calls there
keeps every new case on the existing harness and lets a test assert parameter forwarding and ordering through the one
`calls` list the existing cases already read. Baselines on this branch: 7 passed in `test_postgres_helpers.py`, 69
passed in the demo suite.

**Alternatives considered**: `unittest.mock.AsyncMock` — rejected, the repository's own harness records calls and
enforces one-operation-at-a-time, which is what makes a helper test meaningful; a second fake module — rejected, it
would fork the instrument.

## R6. The demo demonstrates with two private reads, and nothing else there changes

**Decision**: `IdentityStore` gains `_list_persons(limit, offset)` — a bounded, ordered read through `_fetch`,
answering `list[dict[str, Any]]` — and `_count_persons()` — a `count(*)` through `_fetchval`, answering `int`. The
driver-free base, the in-memory store, the action and the routes are untouched; the demo's suite calls both.

**Rationale**: the spec's clarification answer — the maintainer called the demo a shell for building the graph and
asked for two private methods for internal use. Keeping the base and the stub untouched keeps the change additive for
the demo too: no abstract member is added, so no subclass in or out of the repository has to implement one.

**Alternatives considered**: public domain operations on the driver-free base — rejected in the clarification; an
action and an HTTP route — rejected for the same reason, and out of scope in the spec.

## R7. The page states its own order and its own bound

**Decision**: `_list_persons` runs `SELECT id, email, display_name FROM identity_person_hub ORDER BY display_name, id
LIMIT $1 OFFSET $2` and maps each record to a plain `dict`. `_count_persons` runs `SELECT count(*) FROM
identity_person_hub` and converts the answer with `0 if total is None else int(total)`.

**Rationale**: the spec's FR-017 — an example that leaves ordering to the driver teaches the hazard `_fetchrow` is
already documented with. `display_name, id` is deterministic even with duplicate names. The `None` branch is the
value helper's documented "no match answers nothing" path made honest at the call site rather than assumed away.

**Alternatives considered**: `ORDER BY id` only — deterministic but a worse example of a human-ordered page; no
bound — an example that loads a table, the hazard the docs must warn about.

## R8. The module documentation names four helpers in three places

**Decision**: in `postgres_resource.py`, the `ARCHITECTURE / DATA FLOW` diagram gains `_fetch()` and `_fetchval()`
lines beside `_execute()`/`_fetchrow()`; the class's AI-CORE `CONTRACT` key names the four; and the `_execute`
docstring's "a subclass that reads rows uses `_fetchrow`" names both read helpers and when to choose which.

**Rationale**: spec FR-011 and FR-012. The diagram and the `CONTRACT` key are the two places a reader skims before
the code, and the `_execute` docstring is where a developer looking for "how do I read" already is. Constitution
principle IV forbids a block on a method, so the `_execute` sentence changes rather than gaining a block.

**Alternatives considered**: a new module section listing the helpers — rejected, the file already has the diagram
and the contract key, and a third listing would drift.

## R9. The changelog entry is one article under `## [Unreleased]`

**Decision**: `packages/aoa-action-machine/CHANGELOG.md` gains one `### Added` article under `## [Unreleased]`, with
no dated heading, no version bump and no `### Breaking changes` section. `packages/aoa-demo/CHANGELOG.md` is not
touched.

**Rationale**: the maintainer confirmed this in the clarification session, following the correction recorded while
#215 was written. The demo's public surface does not change — the new reads are private and the base is untouched —
so it owes no entry.

**Alternatives considered**: bumping `1.0.1a4` and adding a dated heading, as the issue's wording literally asks —
rejected by the maintainer's answer; an entry in the demo's changelog — rejected, no public change there.

## R10. The documentation example is a page and a count, on both pages

**Decision**: the helper list in `docs/extensions/postgresql.md` ("Installation and construction") and in
`docs/how-to/authoring-resource.md` ("If the implementation uses PostgreSQL") names four helpers, and one worked
example on each shows `_fetch` for a page and `_fetchval` for a count. Both `*.ru_draft.md` counterparts follow.

**Rationale**: spec FR-021 and FR-022. The examples show the two shapes a domain needs — many rows and one value —
and the count example states the `None` branch so a reader does not learn to assume a number.

**Alternatives considered**: documenting the pair only in the API listing — rejected, the pages are where a domain
author is sent, and the issue's acceptance names both pages.

## R11. The new cases live in the pair's existing module, not in a new one

**Decision**: the helper cases are added to
`packages/aoa-action-machine/tests/action_machine/resources/test_postgres_helpers.py`, whose module docstring's
scenario list is extended; the demo's cases go into `packages/aoa-demo/tests/test_identity_postgres.py`.

**Rationale**: the module already exists for exactly this subject ("Tests for the driver's protected helpers"), and
the spec's Assumptions say the structure is kept. Splitting one subject across two files would make the "exactly four
members" case harder to find than the helpers it guards.

**Alternatives considered**: a new `test_postgres_fetch_helpers.py` — rejected as a second home for one subject.

## Open questions

None. Every point the spec left open was answered in its clarification session (demo shape, named parameters,
changelog), and the driver's source settled the rest by measurement. No `NEEDS CLARIFICATION` remains in the plan's
Technical Context.
