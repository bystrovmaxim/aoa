# Baseline searches — the "before" side of this feature's acceptance

**Feature**: `specs/008-driver-fetch-helpers/spec.md` · **Task**: T001 · **Date**: 2026-10-18

These are the searches the specification's acceptance is written in (SC-006, SC-007, SC-009 … SC-012), run **before**
any source change, so that "four afterwards" is a difference and not a claim. This file is the source for the
pull-request description and for the sweep in the closing task (T013); it is not a deliverable of the feature.

## What the baseline stands on

```
$ git rev-parse --short HEAD
9c418a28
$ git rev-parse --short fe4c460e     # the branch base, the release commit
fe4c460e
$ git diff --stat fe4c460e HEAD -- packages docs examples README.md tests scripts pyproject.toml
(empty)
```

The branch base is `fe4c460e` and the committed source tree at the tip is identical to it — the only commit on this
branch, `9c418a28`, adds `specs/008-driver-fetch-helpers/`. Every count below is therefore the state of the
feature's starting point.

Three files are modified in the working tree and are **not** part of this change: they predate the branch and are
named so that a later diff does not read as if this feature touched them —

```
 M examples/step_02_state_as_x-ray_of_the_operation/logs.txt
 M examples/step_02_state_as_x-ray_of_the_operation/traces.txt
 M scripts/deploy_demonstrator_stand.sh
```

They are two example log artefacts and a shell script; none of them is Python, none is under `packages/` or `docs/`,
and none changes a count below.

Environment: CPython 3.12.12, `asyncpg` 0.31.0, package version `1.0.1a4`. The suites are run in this session with
`.venv/bin/python -m pytest` because `uv run` wants its cache under `~/.cache/uv`, outside the sandbox; the
repository's documented form (`uv run --extra dev pytest …`) is what the tasks and quickstart carry.

## S1 — a query member on the SQL shapes

```bash
grep -n "def _\?fetch\|def _\?execute" \
  packages/aoa-action-machine/src/aoa/action_machine/resources/sql/*.py
```

**Before: 0** (exit 1, no hit). **After: 0** — measured at T013, still no hit (FR-013, SC-006).

## S2 — the driver's protected query members

```bash
grep -n "async def _execute\|async def _fetchrow\|async def _fetch\b\|async def _fetchval\b" \
  packages/aoa-action-machine/src/aoa/action_machine/resources/postgres/postgres_resource.py
```

**Before: 2** — `_execute` (`:229`) and `_fetchrow` (`:252`), both over one `_require_connection` (`:223`).
**After: 4** — measured at T013: `:231` `_execute`, `:255` `_fetchrow`, `:279` `_fetch`, `:303` `_fetchval`.
No fifth member (FR-009, SC-006).

## S3 — the pair on the wrapper

```bash
grep -n "def _\?fetch\|def _\?execute" \
  packages/aoa-action-machine/src/aoa/action_machine/resources/sql/wrapper_sql_resource.py
uv run --extra dev python -c "
from aoa.action_machine.resources.sql import WrapperSqlResource as W
assert not hasattr(W, '_fetch') and not hasattr(W, '_fetchval')
print('the wrapper has no query member')"
```

**Before: 0**, and the absence check prints its one line. **After: 0** — measured at T013, and the check still
prints its line: the wrapper does not inherit from `PostgresResource`, so neither member can arrive by inheritance
either (FR-013, SS-1.2).

## S4 — the forbidden convenience family

```bash
grep -rn "_fetchmany\|_executemany\|_fetchval_or\|_fetchrow_or" packages/*/src --include=*.py | wc -l
grep -rln "_fetchmany\|_executemany\|_fetchval_or\|_fetchrow_or" packages/*/src --include=*.py
```

**Before: 36**, and the wide form is useless as a measure — every hit is in one file,
`packages/aoa-maxitor/src/aoa/maxitor/model/diagrams/resources/duckdb_graph_resource.py`, where `_executemany` is a
**module-level function** taking a DuckDB connection (`:495`) plus its 35 call sites. It is not a member of
`PostgresResource`, has nothing to do with the driver in this feature, and predates the branch.

The narrow form is the rule FR-009 states:

```bash
grep -n "_fetchmany\|_executemany\|_fetchval_or\|_fetchrow_or" \
  packages/aoa-action-machine/src/aoa/action_machine/resources/postgres/postgres_resource.py
```

**Before: 0** (exit 1). **After: 0** — measured at T013, and the wide count is still 36: no convenience member
appears beside the four, and Maxitor's function stays as it is, another resource's own helper rather than this API.

This is the second correction of the same kind this feature records: the issue and the first task list said "no hit
under `packages/`", and a wide zero is neither achievable nor what the rule means. `tasks.md` T001 and T013 and
`quickstart.md` §1 now carry the classified form.

## S5 — a domain that reaches for the connection

```bash
grep -rn "self\._conn\|_require_connection\|\.fetch(\|\.fetchval(" \
  packages/aoa-demo/src --include=*.py
```

**Before: 0** (exit 1). The demo's PostgreSQL store already reads only through the protected helpers:
`identity_store.py:55` (`_execute`) and `:62` (`_fetchrow`). The reach-through the issue describes lives in the
consumer outside this repository (bystrovmaxim/gameoffer#72), not in this tree — so the measured promise here is that
the count stays 0 while the two new reads are added. **After: 0** — measured at T013, after `_list_persons` and
`_count_persons` landed (FR-015 … FR-018, SC-007).

## S6 — the new pair anywhere under `packages/`

```bash
grep -rn "_fetch\b\|_fetchval\b" packages/*/src --include=*.py
```

**Before: 0** (exit 1) — the names do not exist yet. **After: 10 mentions**, measured at T013: the two members in
`postgres_resource.py` (`:279`, `:303`) with their diagram, contract and docstring mentions, and the two private
reads that call them in `packages/aoa-demo/src/aoa/demo/model/identity/resources/identity_store.py` (`:72`, `:81`)
with their diagram lines (SC-009).

## S7 — the helpers the pages list

```bash
grep -n "_execute\|_fetchrow\|_fetch\b\|_fetchval\b" \
  docs/extensions/postgresql.md docs/how-to/authoring-resource.md
```

**Before: 2 names per page** — `docs/extensions/postgresql.md:41` and `:44` (the helper list), and
`docs/how-to/authoring-resource.md:144` and `:145` (the paragraph that sends a subclass to them); the same lines
exist in the two `*.ru_draft.md` counterparts (`:41`, `:44` and `:143`, `:144`). **After (T017): 4 names and the
case per page and per draft** — `_execute`, `_fetchrow`, `_fetch`, `_fetchval`, plus the section
"A page through `_fetch` and a count through `_fetchval`" with its Python and notebook links on the PostgreSQL
page, and the page-and-count methods on the authoring page (FR-021, FR-022, SC-010, SC-013).

## S8 — the suites the change must keep green

```
$ .venv/bin/python -m pytest packages/aoa-action-machine/tests/action_machine/resources/test_postgres_helpers.py -q
7 passed
$ .venv/bin/python -m pytest packages/aoa-demo/tests -q
69 passed
```

**Before: 7 and 69.** **After (T013): 22 and 73** — the helper module grew by the 15 page, value and policy cases,
the demo by the 4 read cases, all with no database. The two contract suites are unedited (`git diff` empty) and
pass at 65; the resources suite is 144 and the whole machine suite 2543 (SC-008, SC-011).

## After — measured 2026-10-18 (T013)

| Search | Before | After | Acceptance |
| --- | --- | --- | --- |
| S1 — query member on the SQL shapes | 0 | **0** | SC-006 |
| S2 — protected query members on the driver | 2 | **4** | SC-006 |
| S3 — pair on the wrapper | 0 | **0** | SC-006 |
| S4 — forbidden family on the driver | 0 | **0** (wide still 36, Maxitor, unchanged) | FR-009 |
| S5 — demo reaching for the connection | 0 | **0** | SC-007 |
| S6 — the pair under `packages/` | 0 | **10 mentions** (two members, two reads) | SC-009 |
| S7 — helpers named per page | 2 per page | **4 per page**, plus the case and its two links | SC-010, SC-013 |
| S8 — suites | 7 / 69 | **22 / 73** (+144 resources, 2543 machine) | SC-008, SC-011 |

The T013 commands also ran the two contract suites **unedited**: `test_sql_resource.py` and
`test_wrapper_sql_resource.py` carry no diff and pass (65 cases), which is what SC-011 and SC-012 are about.
S7 was the one row left open by T013; T017 closed it when the documentation landed, and the row above carries the
measured "after".

## vulture (T015)

```
$ .venv/bin/python -m vulture
(no output)
rc=0
```

Green, at the configured `min_confidence = 80`. What it cannot show is a caller: an unused method carries 60 %, so
the check would pass with either helper uncalled. The evidence that each has one is S6's search and the demo's two
private reads; the threshold was not lowered and no annotation or `# noqa` was added. The check does catch an unused
import, and this change adds none — the driver module already imported `Any`.
