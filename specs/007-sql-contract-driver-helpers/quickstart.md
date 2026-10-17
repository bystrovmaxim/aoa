# Phase 1 — Quickstart: The query surface leaves the SQL contract, and the driver keeps protected helpers

**Feature**: `specs/007-sql-contract-driver-helpers/spec.md` · **Date**: 2026-10-17

This is the run guide: every command below is meant to be pasted from the repository root, and every one states what
it must print. It proves the change end to end without a database. Commands that need the driver use
`--extra dev`, which already carries `aoa-action-machine[postgres]`; no test and no example needs a live PostgreSQL.

The contracts behind these checks are [sql-resource.md](./contracts/sql-resource.md),
[driver-helpers.md](./contracts/driver-helpers.md) and [nested-access.md](./contracts/nested-access.md); the shapes
are in [data-model.md](./data-model.md).

## 0. Prerequisites

```bash
cd /path/to/aoa
uv sync --extra dev                       # asyncpg arrives through aoa-action-machine[postgres]
python -c "import asyncpg; print(asyncpg.__version__)"   # 0.31.0 here
```

No PostgreSQL server is started, and no `DSN` is set anywhere.

## 1. Prove the member is gone, and that the shapes still hold

```bash
uv run --extra dev python -c "
from aoa.action_machine.resources.sql import ProtocolSqlResource, SqlResource, WrapperSqlResource
for shape in (ProtocolSqlResource, SqlResource, WrapperSqlResource):
    assert not hasattr(shape, 'execute'), shape
print('no public query member on the contract, the base and the proxy')
"
```

Expect that one line. Then the source search, which is what the pull request quotes:

```bash
grep -rn "def execute" packages/*/src --include=*.py
```

Expect **no** hit among the four SQL shapes; the only hits are unrelated members of the runtime
(`runtime/saga_coordinator.py`, `runtime/aspect_executor.py`). And the caller search:

```bash
grep -rn "\.execute(" packages/*/src --include=*.py
```

Expect **only** the driver's own lifecycle statements — `self._conn.execute("BEGIN" | "COMMIT" | "ROLLBACK")` in
`resources/postgres/postgres_resource.py` — and no call of a member on a resource.

## 2. The helpers: the check, the wrap, the row

```bash
uv run --extra dev pytest packages/aoa-action-machine/tests/action_machine/resources/test_postgres_helpers.py -v
```

Expect all green. Each test names the case it proves:

- a helper on a resource that never opened, and on one already closed, raises `HandleError("Connection is not open")`
  — and the test asserts the exception type, so an attribute error cannot pass for it;
- a connection that refuses a statement produces `HandleError` whose `__cause__` is the driver's error, and the test
  asserts the cause rather than the message alone;
- parameters reach the connection as positional arguments, and `None` and `()` behave the same;
- `_fetchrow` returns the row the fake connection holds, and `None` when it holds none.

The fake is `packages/aoa-action-machine/tests/support/fake_pool.py`; it answers `fetchrow` with the same
one-operation-at-a-time rule its `execute` already enforces, so the helper tests cannot pass on a connection that
quietly serializes.

## 3. The contract and the base without the fourth abstract member

```bash
uv run --extra dev pytest \
  packages/aoa-action-machine/tests/action_machine/resources/test_sql_resource.py \
  packages/aoa-action-machine/tests/action_machine/resources/test_resource_unit_of_work.py -v
```

Expect green. The incomplete-subclass cases cover `open`, `begin` and `rollback` only — the "missing `execute`" case
is deleted — and a subclass implementing exactly those three instantiates and takes `commit` from the base. The
unit-of-work cases keep asserting what `#215` established, now driving the statement helper instead of the removed
member.

## 4. The proxy delegates nothing and still satisfies the contract

```bash
uv run --extra dev pytest packages/aoa-action-machine/tests/action_machine/resources/test_wrapper_sql_resource.py -v
```

Expect green with these cases present: `execute`, `_execute` and `_fetchrow` are absent from the proxy; `open`,
`begin`, `commit`, `rollback`, `close`, `__aenter__` and `__aexit__` are refused with `TransactionProhibitedError`;
`isinstance(proxy, ProtocolSqlResource)` is true; a second and a third wrap behave as the first; and a domain wrapper
delegates its own semantic method while the lifecycle stays refused.

## 5. The demo, with no database

```bash
uv run --extra dev pytest packages/aoa-demo/tests -v
```

Expect green, and in particular:

- `test_sql_resource_stubs.py` — the eight stubs still satisfy the contract and still close harmlessly, now without
  the removed member;
- `test_identity_postgres.py` — the domain's read answers one person or `None` through the row helper, the write
  commits inside the transaction `record_login` owns, and a read on a closed resource raises
  `HandleError("Connection is not open")` rather than the base's own error.

The database-free mode is the same command: no `AOA_DEMO_POSTGRES_DSN` is set, so the route answers from the
in-memory store, and the PostgreSQL store is exercised over the fake pool.

## 6. The examples, and the case that is gone

```bash
uv run python examples/step_19_resource/07_nested_action.py      # the domain wrapper, and the refusal
uv run python examples/extensions/postgresql/14_failed_commit.py # a domain method over the helper
uv run python examples/step_17_connections/16_pool_lifespan.py   # the semantic method over the helper
```

Each must exit 0 and print its own observable result. Then the pair check and the full runner, which the closing
check run does **not** include:

```bash
test -f examples/step_19_resource/04_wrapper_execute.py && echo "STILL THERE" || echo "deleted"
uv run --extra dev pytest tests/examples -v
```

Expect `deleted`, and expect the runner green apart from its four documented `xfail` entries, none of which this
feature touches. Every edited script has its notebook beside it, rebuilt from the same blocks and executed cell by
cell; the tutorial's links to the deleted case are gone.

## 7. The documentation no longer teaches the passthrough

```bash
grep -rn "wrapper can execute\|delegates execute\|execute(query" docs README.md
```

Expect no hit that presents the removed member as the SQL query surface. The pages that keep their own `execute` —
the in-memory ledger in `docs/how-to/authoring-resource.md`, `docs/tutorials/step-06-dependencies.md` — are
expected hits and are deliberately untouched. The PostgreSQL page, the authoring page and the tutorial instead name
the two helpers, and the tutorial's nested-action section shows a resource's own wrapper delegating its own method.

The two Russian drafts that carry the rewritten prose are updated in the same change and reported beside their
English pages:

```bash
ls -l docs/extensions/postgresql.ru_draft.md docs/tutorials/step-19-resource.ru_draft.md
git status --short | grep ru_draft || echo "drafts are gitignored, as intended"
```

## 8. The adversarial break, both directions

With the suite green, break the code the new tests exist to catch, one break at a time, from a byte-for-byte backup:

1. **The absence of the query member.** Add a delegating `execute` back to `WrapperSqlResource`. Expect the absence
   tests in `test_wrapper_sql_resource.py` red, and nothing else. Restore.
2. **The single check.** Make `_require_connection` return `self._conn` without testing it. Expect the
   closed-resource tests in `test_postgres_helpers.py` and the demo's closed-resource test red — and, where a helper
   then dereferences `None`, an `AttributeError`, which is the symptom the check exists to prevent. Restore.
3. **The chained cause.** Raise `HandleError` without `from e`. Expect exactly the cause assertion in
   `test_postgres_helpers.py` red. Restore.

After each restore, `diff -q` against the backup must be clean and the suite green again. The three breaks and their
failure lists are what the pull request pastes.

## 9. The closing check run

```bash
bash scripts/run_checks_with_log.sh
```

Expect exit 0 with every step `OK`, and exactly two remarks in the log: the Vite chunk-size advisory and
LangGraph's pending-deprecation warning. Anything else — a `ruff` finding, a `mypy` error on the protected names, a
`vulture` unused import, a failing package suite — is fixed in the change, not triaged away.

## What "done" looks like

- No public query member exists on the contract, the base, the proxy or the driver, and the driver answers exactly
  two protected helpers, each with a caller inside `packages/`.
- A helper on a resource that is not open raises the framework's named failure, and a driver failure arrives with
  the driver's error chained.
- The proxy exposes no query member and still satisfies the contract; a domain wrapper delegates its own method and
  still refuses the lifecycle.
- The demo runs with and without a database, and its in-memory store no longer reads statement text.
- The pages, the home page and the examples teach semantic methods over the helpers; the case that taught the
  passthrough is gone with its notebook and its section.
- The changelog carries one breaking-change entry under `## [Unreleased]` naming both replacements, with no dated
  heading and no version bump.
- The check run is green with only the two accepted remarks, and the examples runner is green.

## What would make this quickstart lie

- **Running only the check run.** `scripts/run_checks_with_log.sh` never executes `tests/examples`
  (`:168` runs `tests/packaging` and then the eight package suites), so a broken example stays invisible. Section 6
  is not optional.
- **Trusting the greps at the tip only.** A stale fragment can predate the branch; the searches must be run against
  the branch base `1e4c6b02` too, and the pull request quotes both.
- **A fake that cannot fail.** If `FakeConnection.fetchrow` ignores the statement or the one-operation rule, the
  helper tests pass vacuously. The fake records the statement and the parameters, and rejects a concurrent operation
  the way the driver does.
- **Reshaping the read without the action.** If `read_person` returns one row while `identity_lookup` still treats it
  as a list, the route reports `found=True` with empty fields instead of failing loudly; the action's `is None` test
  is part of the same change.
- **Leaving the prose behind.** A docstring that still names the removed member, or a tutorial section that still
  shows the deleted case, turns a green suite into documentation that lies — which is why the prose is part of the
  four shapes' contract (SR-1.3) and of the documentation task.
