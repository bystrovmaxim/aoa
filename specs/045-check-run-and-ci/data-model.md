# Data Model — Check run and CI

The feature's "data" is the table of steps and the selectors that choose a subset of it. There is no persisted domain data; this file fixes the shape of the step table and the home vocabulary so the implementation and the tests agree.

## Entity: `Step`

One row of the step table in `scripts/check_run.py`.

| Field | Type | Meaning | Validation |
|---|---|---|---|
| `name` | str | The row's identity and log heading. | Unique in the table. |
| `command` | str | The `bash -c` line, run from the repo root. | Non-empty. |
| `group` | str | Coarse grouping (`first`, `client`, `static`, `packaging`, `tests`, `graphs`). | One of the known groups. |
| `home` | `"local" \| "ci" \| "both"` | Where the step belongs. | Default `"both"`; must be one of the three. |
| `fast` | bool | Runs in the local fast mode. | Default `False`. |
| `browser` | bool | Launches a real browser engine. | Default `False`. |
| `after` | tuple[str, ...] | Steps that must end first. | Names refer to table rows. |
| `not_during` | tuple[str, ...] | Steps that must not overlap. | Names refer to table rows. |
| `shown` | str | The command the log prints, when it differs. | — |
| `blank_before_result` | bool | Log formatting. | Default `True`. |
| `only_if_all_passed` | bool | Runs only when every other step passed; the steps that wait for it do not count. | Default `False`. |
| `ci_command` | str | The command under `--where ci`, and under `--fast` for the rows it keeps. | Default empty: `command` everywhere. |

`name` stays the unique key; `home`, `fast` and `browser` are the three axes the selectors read.

## Entity: selector

The set of flags that chooses which rows run.

| Selector | Rows kept |
|---|---|
| `--where local` (default) | `home ∈ {local, both}` |
| `--where ci` | `home ∈ {ci, both}` |
| `--where both` | every row |
| `--fast` | `fast == True` (local only) |
| `--only-browser` | `browser == True` plus the client build it needs |
| `--only-group NAME` | `group == NAME` |
| `--skip-group NAME` | `group != NAME` |

Selectors compose by intersection. `only_*` selectors ignore `home` and pick the named rows regardless; this is what lets one CI job run only the browser step and another only packaging.

## Entity: home assignment

The decision of the spec, as data. This is the table the implementation must reproduce; see [spec.md](./spec.md#decision-table) for the reasons.

| Row | home | fast | browser |
|---|---|---|---|
| Ban `__getattr__` in package `__init__.py` | both | ✅ | — |
| Maxitor client: README beside `components/*/index.ts` | both | ✅ | — |
| Ruff auto-fix (`ruff check --fix`) | local | ✅ | — |
| Ruff lint | both | ✅ | — |
| Mypy typecheck | both | ✅ | — |
| Pylint | both | ✅ | — |
| Package import boundaries | both | ✅ | — |
| Package metadata | both | ✅ | — |
| Vulture dead code | both | ✅ | — |
| Maxitor samples: public API | both | ✅ | — |
| Radon cyclomatic complexity | both | ✅ | — |
| Radon maintainability index | both | ✅ | — |
| Maxitor client: `npm ci` and Vite build | both | — | — |
| Maxitor client: unit tests (vitest) | both | — | — |
| Maxitor client: three-engine layout | local | — | ✅ |
| Maxitor client: ERD scripts (5×, Graphviz WASM) | both | — | — |
| Pytest — 12 package dirs (benchmarks excluded in CI) | both | ✅ | — |
| Pytest — `tests/scripts` | both | ✅ | — |
| Build wheel/sdist ×8 | ci | — | — |
| Packaging wheel install smoke | ci | — | — |
| Graph files: write | local | — | — |
| Graph files: check | both | — | — |

`fast` is true only for the rows that need neither the client build nor a real browser; the Python suites, the guards and the static checks qualify.

## The CI command variant

A row may carry `ci_command`: the command run under `--where ci`, and under `--fast` for the rows the fast mode keeps, used where the same suite must differ on a gate that is deterministic. The Python suites use it to exclude the speed tests without a second row: the full local run runs everything, CI and the fast mode run `-m "not benchmark"`. The five speed-sensitive files are marked `benchmark` — the four wholly-speed files at module level, the rate-limit test in `test_websocket_route.py` individually so the route's ordinary tests keep running in CI.

## Entity: receipt

`archive/logs/check-run-receipt.json`, outside Git, left by a green full local run: `{"commit": "<sha>", "steps": <count>}`.

| Rule | Why |
|---|---|
| Written only when the selection is the whole local run | A narrow run proves less. |
| Written only when the tree was one commit from start to end | An auto-fix or a graph write changes what was proved. |
| Dropped when a whole run starts | The latest run speaks for the commit, so a red one takes back an earlier green one. |

## Entity: sign-off

The commit status `Local check run`, state `success`, on the commit the receipt names. `--sign-off` posts it; the CI job `Proof of the local run` reads it through `--await-sign-off <commit>` and passes on `success` alone.
