# Quickstart: validating the check-run gates

Run everything from the worktree root, `/Users/bystrovmaxim/PythonDev/aoa-issue-296`. Every deliberate break is restored before the next.

## Times before the change

Record these on the untouched tree, and again at the end of each phase.

```bash
time uv run --extra dev task cc
time uv run --extra dev task mi
time bash scripts/check_before_commit.sh
```

## Package builds (User Story 3)

For each of the eight packages, in a scratch directory outside the repository:

1. Build with `uv build --package <name> --out-dir <scratch>/uv`.
2. Build with `uv run --extra dev --with build python -m build packages/<path> --outdir <scratch>/pip`.
3. Compare member lists of each wheel (`unzip -Z1`) and each sdist (`tar tzf`).

Expected: identical lists for all eight, with both times recorded. `maxitor`'s sdist packs the client, so build the client first.

## Complexity gate (User Story 1)

| Break | Expected from `task cc` |
|---|---|
| None, gate on, six functions simplified | Exit 0 |
| Add branches to a function until complexity is 21 | Exit 1, naming it with grade D |
| The same function at complexity 20 | Exit 0 |
| Two such functions | Exit 1, naming both |
| An exception for a function not over the limit | Exit 1, stale |
| An exception with an empty reason | Exit 1 |
| A file with a syntax error under `packages/` | Exit 1, naming the file |

Each row is also a test in `tests/scripts/test_check_radon.py`, and each test is proved by the adversarial break of the rule: break the rule in the script, see that test fail and no other, restore.

## Maintainability gate (User Story 1)

| Break | Expected from `task mi` |
|---|---|
| None, `test_graph_map.py` dealt with | Exit 0 |
| Make one module grade B | Exit 1, naming it |

## Ruff (User Story 2)

| Break | Run | Expected |
|---|---|---|
| Unfixable error, such as an undefined name | `bash scripts/check_before_commit.sh` | Fails at "Ruff auto-fix" |
| Fixable error, such as an unused import | `bash scripts/check_before_commit.sh` | Fixed, passes that step |
| Fixable error | `bash scripts/run_checks_with_log.sh --where ci --skip-group packaging` | Fails at "Ruff auto-fix"; `git status` shows the error still there |

The step list holds one Ruff row in the local, `--fast` and CI selections; `tests/scripts/test_check_run.py` holds this.

## Closing

```bash
bash scripts/run_checks_with_log.sh
```

Expected: green, with only the two accepted remarks, and wall time no higher than the time recorded before.
