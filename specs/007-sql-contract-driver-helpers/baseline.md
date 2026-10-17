# Baseline searches — the "before" side of this feature's acceptance

**Feature**: `specs/007-sql-contract-driver-helpers/spec.md` · **Task**: T001 · **Date**: 2026-10-17

These are the searches the specification's acceptance is written in (SC-001, SC-010, SC-012, SC-013, SC-017), run
**before** any source change, so that "0 afterwards" is a difference and not a claim. This file is the source for
the pull-request description and for the sweep in the closing task (T027); it is not a deliverable of the feature.

## What the baseline stands on

```
$ git rev-parse --short HEAD
2a9f5386
$ git diff --stat 1e4c6b02 HEAD -- packages docs examples README.md tests scripts pyproject.toml
(empty)
```

The branch base is `1e4c6b02` and the source tree at the tip is identical to it — the only commit on this branch
adds `specs/007-sql-contract-driver-helpers/`. Every count below is therefore the state of the feature's
starting point.

## S1 — a public query member on a SQL shape

```bash
grep -rn "def execute" packages/aoa-action-machine/src/aoa/action_machine/resources \
                        packages/aoa-demo/src/aoa/demo/model --include=*.py | wc -l
```

**Before: 13** — the four shapes (`protocol_sql_resource.py:76`, `sql_resource.py:148`,
`wrapper_sql_resource.py:133`, `postgres_resource.py:223`), the eight demo stubs (each at `:26` of its own module),
and the demo's in-memory identity store (`identity_store_stub.py:67`). **After: 0** (SC-001).

## S2 — a call of that member through a resource

The wide form (`grep -rn "\.execute(" packages/*/src`) returns 48 hits and is useless as a measure: Maxitor's
DuckDB resource calls `con.execute(...)` on its own cursor (untouched, `FR-024`), and the runtime's
`SagaCoordinator.execute` is a different member. The narrow form keeps the distinction:

```bash
grep -rn "\.execute(" packages/aoa-action-machine/src packages/aoa-demo/src \
                      packages/aoa-fastapi-adapter/src packages/aoa-mcp-adapter/src --include=*.py \
  | grep -v "_conn\.execute"
```

**Before: 7**, in two groups.

| Group | Sites | After |
| --- | --- | --- |
| The SQL contract's own member | `sql_resource.py:52`, `:53` (the rollup walk-through writes statements through it) and `wrapper_sql_resource.py:136` (the proxy's delegation) | **0** — both go with the member (FR-002, FR-003) |
| The demo's caller | `identity_store_base.py:74` (`record_login` calls the member) | **0** — it calls the domain's own write primitive instead (FR-016) |
| Unrelated members, expected to stay | `saga_coordinator.py:22`, `action_product_machine.py:49` (both docstrings) and `action_product_machine.py:532` (the real call) | **3** — `SagaCoordinator.execute` is not the SQL contract and is out of scope |

So the measured target is **4 SQL-contract sites to 0**, with 3 unrelated hits remaining and named in advance
(SC-010).

## S3 — a page presenting it as the SQL query surface

```bash
grep -rn "execute(query\|delegates execute\|super().execute\|wrapper can execute" docs README.md
```

**Before: 7**, in four files — `docs/extensions/postgresql.md` (`:35`, `:614`, `:650`), its Russian draft
(`:35`, `:615`), `docs/how-to/authoring-resource.md` (`:118`) and `docs/tutorials/step-19-resource.md` (`:225`).
**After: 0** — all four pages are rewritten, and the tutorial's section is deleted (SC-013).

## S4 — a store that decides what to do from statement text

```bash
grep -rn "startswith(\"INSERT\")" packages/*/src --include=*.py
```

**Before: 1** — `packages/aoa-demo/src/aoa/demo/model/identity/resources/identity_store_stub.py:69`, a store with
no database parsing SQL to find out what it was asked to do. **After: 0** (SC-017).

The scope is `packages/*/src`, and that is deliberate: the rule is about a *store* deciding from statement text, and
a test may legitimately filter the calls it recorded by their statement — which is what the demo's interleaving test
does to tell its two units apart. Counting the tests would make the criterion say something it does not mean.

## S5 — examples that call the member

```bash
grep -rn "\.execute(" examples --include=*.py
```

**Before: 11**, in two groups.

| Group | Sites | After |
| --- | --- | --- |
| The SQL contract | `step_17_connections/16_pool_lifespan.py:99`; `extensions/postgresql/02_concurrent.py:80`, `04_commit.py:70`, `05_rollback.py:72`, `07_rollup.py:70`, `14_failed_commit.py:73`; `step_19_resource/04_wrapper_execute.py:74` (deleted) and `07_nested_action.py:99` | **0** — seven scripts migrated in T017, one deleted there, one enriched in T019 (SC-009, SC-018) |
| A resource's own member | `step_06_dependencies/01_depends.py:99`, `:132`, `:173` (the in-memory ledger's own `execute(entry)`) | **3** — untouched by design (FR-024) |

## How the same searches are run at the end

T027 runs all five against the branch base **and** the tip, and the pull request quotes both columns. The only
accepted remaining hits are the three unrelated runtime members of S2 and the three ledger calls of S5, each named
above before the change rather than excused after it.
