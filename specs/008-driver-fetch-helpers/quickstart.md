# Phase 1 — Quickstart: A domain reads all rows and one value through the driver's protected helpers

**Feature**: `specs/008-driver-fetch-helpers/spec.md` · **Date**: 2026-10-18

This is the run guide: every command below is pasted from the repository root, and each states what it must print.
It proves the change end to end with no database. `--extra dev` already carries `aoa-action-machine[postgres]`, so
the driver is present; no server is started and no `DSN` is set anywhere.

The contracts behind these checks are [fetch-helpers.md](./contracts/fetch-helpers.md),
[sql-surface.md](./contracts/sql-surface.md) and [demo-reads.md](./contracts/demo-reads.md); the shapes are in
[data-model.md](./data-model.md).

## 0. Prerequisites

```bash
cd /path/to/aoa
uv sync --extra dev
uv run --extra dev python -c "import asyncpg; print(asyncpg.__version__)"
```

Expect `0.31.0` (or the installed version within `>=0.29,<1.0`). Measured on this branch before the change, the two
suites this feature touches are green: `test_postgres_helpers.py` 7 passed, the demo suite 69 passed.

## 1. The driver offers four query helpers and no fifth

```bash
grep -n "async def _execute\|async def _fetchrow\|async def _fetch\b\|async def _fetchval\b" \
  packages/aoa-action-machine/src/aoa/action_machine/resources/postgres/postgres_resource.py
```

Expect exactly four lines. Then the negative:

```bash
grep -rn "_fetchmany\|_executemany\|_fetchval_or\|_fetchrow_or" packages/*/src --include=*.py
```

Expect no hit.

## 2. The pair's answers

```bash
uv run --extra dev pytest \
  packages/aoa-action-machine/tests/action_machine/resources/test_postgres_helpers.py -v
```

Expect every case to pass, with the new ones named for what they prove: the empty list, the list of one, several
rows with and without `ORDER BY`, the scalar rather than the row, no match answering nothing, the closed resource,
the chained failure, and the parameter shapes.

A direct look at the shapes, over the fake pool the suite uses:

```bash
uv run --extra dev python - <<'PY'
import asyncio
import sys

sys.path.insert(0, "packages/aoa-action-machine")   # the machine's own test-support package

from aoa.action_machine.resources.postgres.postgres_resource import PostgresResource
from tests.support.fake_pool import FakePool

async def main():
    pool = FakePool(max_size=1)
    resource = PostgresResource(pool=pool)
    await resource.open()
    connection = next(iter(pool.borrowed))
    connection.rows = [{"id": "p1"}, {"id": "p2"}]
    print(await resource._fetch("SELECT id FROM t ORDER BY id"))   # the two rows, as a list
    print(await resource._fetch("SELECT id FROM t WHERE false"))    # []
    connection.value = 2
    print(await resource._fetchval("SELECT count(*) FROM t"))       # 2, not a row
    connection.value = None
    print(await resource._fetchval("SELECT count(*) FROM t WHERE false"))  # None
    await resource.close()

asyncio.run(main())
```

Expect:

```text
[{'id': 'p1'}, {'id': 'p2'}]
[]
2
None
```

`rows` and `value` are the two attributes §R5 of [research.md](./research.md) adds to `FakeConnection`. If the
snippet cannot find the support package, run the suite in §2 instead — it asserts the same four answers.

## 3. One check, one error

The suite's closed-resource and chained-failure cases in §2 are the proof; to see them by name:

```bash
uv run --extra dev pytest \
  packages/aoa-action-machine/tests/action_machine/resources/test_postgres_helpers.py \
  -k "without_a_connection or closed_resource or failing_connection" -v
```

Expect the named `Connection is not open` cases and the `SQL execution failed` case with its cause. No `AttributeError`
is raised, and no driver exception type escapes.

## 4. Parameters

```bash
uv run --extra dev pytest \
  packages/aoa-action-machine/tests/action_machine/resources/test_postgres_helpers.py \
  -k "parameters or empty_tuple" -v
```

Expect both to pass: the parameters reach the connection positionally, and `None` and `()` are the same call.

## 5. The demo's two reads

```bash
uv run --extra dev pytest packages/aoa-demo/tests -v
```

Expect the previous 69 plus the new cases, all green with no database and no `postgres` extra import at module load.
The new cases prove the list answers mappings with an `ORDER BY` and a `LIMIT`/`OFFSET`, the count answers an `int`,
and the faked connection recorded `fetch` and `fetchval` rather than the connection being touched.

The two reads by name:

```bash
uv run --extra dev pytest packages/aoa-demo/tests -k "list_persons or count_persons" -v
```

## 6. The SQL surface did not move

```bash
grep -n "def _\?fetch\|def _\?execute" \
  packages/aoa-action-machine/src/aoa/action_machine/resources/sql/*.py
```

Expect no hit. And the protocol and wrapper suites:

```bash
uv run --extra dev pytest \
  packages/aoa-action-machine/tests/action_machine/resources/test_sql_resource.py \
  packages/aoa-action-machine/tests/action_machine/resources/test_wrapper_sql_resource.py -q
```

Expect all cases green, unedited — including the `isinstance(wrapper, ProtocolSqlResource)` case and the refusals.

## 7. The docs and the changelog

```bash
grep -n "_execute\|_fetchrow\|_fetch\|_fetchval" docs/extensions/postgresql.md docs/how-to/authoring-resource.md
```

Expect each page to name the four helpers, with the page-and-count example present in both. The Russian drafts
beside them:

```bash
grep -n "_execute\|_fetchrow\|_fetch\|_fetchval" \
  docs/extensions/postgresql.ru_draft.md docs/how-to/authoring-resource.ru_draft.md
```

Expect the same four names in each. `*_draft.md` is gitignored and does not enter the commit.

```bash
sed -n '1,20p' packages/aoa-action-machine/CHANGELOG.md
```

Expect one `### Added` article under `## [Unreleased]`, with no dated heading and no `### Breaking changes`.

## 8. The adversarial breaks

Each of these is made on purpose, run against the suite, and reverted. The point is that the new checks catch the
defect they exist for, and that no other case fails.

| Break | Expected failures |
| --- | --- |
| `_fetch` returns `self.row` instead of the rows | the empty-list and several-rows cases |
| `_fetchval` returns the row instead of its first value | the scalar case |
| both helpers read `self._conn` directly | the closed-resource and never-opened cases (`AttributeError`) |
| the driver error is raised unwrapped | the chained-failure cases |
| `_fetch` passes `params` as one argument instead of `*params` | the parameter and empty-tuple cases |
| `WrapperSqlResource` gains a delegating `_fetch` | the "exactly four members" and wrapper-absence cases |
| the demo's list read drops `ORDER BY`/`LIMIT` | the demo's list case |
| the demo's count read returns the record | the demo's count case |

After each break: restore the file, re-run the module, and confirm the suite is green again.

## 9. The example

```bash
uv run python examples/extensions/postgresql/15_fetch_and_fetchval.py
uv run --extra dev pytest tests/examples -q
```

Expect the script to print the page and the count, and the examples runner to pass. The repository-wide check run
does not execute examples, so this is its own gate.

## 10. The closing check run

```bash
bash scripts/run_checks_with_log.sh
```

Expect a clean run. The two remarks allowed to stand are the Vite chunk-size advisory and LangGraph's
pending-deprecation warning, both named in the script and in the constitution. Anything else is fixed in the change
rather than triaged away.
