# Run the checks

No change in this repository is finished until the check run is green, and each check runs once:

| When | Where | What runs |
|------|-------|-----------|
| After each phase | your machine | the tests of that phase |
| On a pull request | CI | the closing check run: the guard, static checks, Python tests, the examples, packaging |

A pull request that changes only `docs/`, `specs/`, `AGENTS.md` or the constitution skips CI's checks: the job `Changes` sees that, and a skipped job counts as passed.

The merge rule of `main` requires a green CI, and nothing else: every check of this repository runs on a CI machine. One command is the full gate on its own, for when you want everything on your machine. No step requires it:

```bash
bash scripts/run_checks_with_log.sh
```

It runs the repository guard, Ruff, mypy, pylint, the package-boundary and package-metadata checkers, the secrets check, vulture, the samples public-API check, every example of the documentation, the tests of every package, Radon, and a check of the saved graph file — and writes everything they print into one log, `archive/logs/check-all.txt`. The wheel and sdist build and the packaging smoke test are **not** part of the local run: they need the network and matter when a package is released, so CI runs them. Steps that do not depend on each other run at the same time, so the run takes about as long as its slowest step instead of the sum of all of them.

Maxitor, its client and the check that draws it in three browser engines live in [bystrovmaxim/gnomon](https://github.com/bystrovmaxim/gnomon), and run there.

This page shows each case as the command and what it really printed.

## A normal run

The console shows each step when it starts (`>`) and when it ends, with its exit code and how long it took. Steps end in whatever order they finish:

```text
Log file: /Users/bystrovmaxim/PythonDev/aoa/archive/logs/check-all.txt

Full check run (cwd=/Users/bystrovmaxim/PythonDev/aoa, up to 14 steps at once)...

> Ban __getattr__ in package __init__.py
OK Ban __getattr__ in package __init__.py (exit 0, 0.5 s)
> Ruff auto-fix
OK Ruff auto-fix (exit 0, 0.1 s)
> Mypy typecheck
> Pylint
…
OK Pytest aoa-fastapi-adapter (exit 0, 26.2 s)
OK Examples: scripts, notebooks, pages, links (exit 0, 78.8 s)
OK Pytest aoa-action-machine (exit 0, 153.8 s)
> Graph files (graph-builder write)
OK Graph files (graph-builder write) (exit 0, 1.1 s)
> Graph files (graph-builder check)
OK Graph files (graph-builder check) (exit 0, 1.0 s)

Wall time: 156.8 s
Log: /Users/bystrovmaxim/PythonDev/aoa/archive/logs/check-all.txt
```

The exit code is 0 when every step passed. The run may edit code: `Ruff auto-fix` rewrites what it can fix, and those edits belong to your change like any other.

## How the log reads

The log is written when the run ends. Whatever ran at the same time, it lists every step **in one fixed order**, each in its own block — the step's name, its command, everything it printed, and its result line — between a header and a footer:

```text
==================================================
ActionMachine project checks
Date: Wed Oct 28 14:31:33 MSK 2026
Time: 14:31:33
Repository: /Users/bystrovmaxim/PythonDev/aoa
==================================================

=== Ban __getattr__ in package __init__.py ===
…
=== Ruff auto-fix ===
$ uv run --extra dev ruff check --fix packages/ tests/ scripts/

All checks passed!

OK Ruff auto-fix (exit 0, 0.1 s)

…
==================================================
All steps finished (see FAIL lines above or in the log if anything failed)
Wall time: 57.0 s
Log: /Users/bystrovmaxim/PythonDev/aoa/archive/logs/check-all.txt
==================================================
```

A block holds only its own step's output, so two steps' lines never mix. One remark is known and accepted, and stays in a green run: LangGraph's `LangChainPendingDeprecationWarning`. It comes from the library, not from this repository's code.

## What runs together and what waits

The steps, their order and what each waits for are one table in `scripts/check_run.py`. The rules come from what the steps read and write:

| Group | Steps | Waits for |
|---|---|---|
| First, alone | the guard, then `Ruff auto-fix` | nothing; nothing else runs meanwhile, because the auto-fix rewrites files every later Python step reads |
| Static analysis | mypy, pylint, package boundaries, package metadata, no secrets in tracked files, vulture, samples public API, Radon | the auto-fix |
| Tests | the tests of each package, one run per package, and `tests/scripts` (the runner's own last-step rule, the saved graph file) | the auto-fix |
| Examples | every example of the documentation ([Examples](#examples)), in a group of its own so CI can run it on a machine of its own | the auto-fix |
| Only on a green run | `Graph files (graph-builder write)`: builds the repository's graph and updates its file ([graph-builder](https://github.com/bystrovmaxim/gnomon/blob/main/packages/maxitor/tools/graph-builder/README.md), installed with `maxitor` from PyPI) | every other step except the graph check; if any failed, it does not run and its block reads `SKIPPED Graph files (graph-builder write): N step(s) failed` — neither `OK` nor `FAIL` |
| Last, always | `Graph files (graph-builder check)`: verifies the saved graph files are current | the graph write; it runs even when another step failed |

The graph write may change `packages/aoa-demo/graph.json`, as the auto-fix may change sources; the run stays green, and the changed files go into the commit with the change that changed the graph. The check comes after it, so a stale file is rewritten on a green run instead of failing it:

```text
OK Graph files (graph-builder write) (exit 0, 3.8 s)
OK Graph files (graph-builder check) (exit 0, 1.9 s)
```

After a failure elsewhere the write is skipped and the check still reports, so the files are never left neither written nor checked. The seven package builds and the packaging smoke test are not in the local table: they run only in CI.

The run is as long as its slowest step, and today that is the tests of `aoa-action-machine`, about 150 s when everything runs at once. Every other step finishes beside it, so only making that step shorter makes the run shorter.

## Where each step runs

Every step has one stated home. The same table in `scripts/check_run.py` drives the local run and every CI job, and each context selects its rows:

| Step | Local run | CI | Why |
|---|---|---|---|
| Ban `__getattr__` in package `__init__.py` | ✅ | ✅ | cheap guard, no network |
| Ruff auto-fix | ✅ fixes | ✅ only reports | CI must not change the tree |
| Mypy, pylint | ✅ | ✅ | deterministic static checks |
| Package boundaries, package metadata | ✅ | ✅ | deterministic static checks |
| No secrets in tracked files | ✅ | ✅ | deterministic; a commit made without the local hook still meets it in CI |
| Vulture, samples public API, Radon | ✅ | ✅ | deterministic static checks |
| Python tests of every package, `tests/scripts` | ✅ | ✅ | deterministic |
| The examples | ✅ | ✅ (jobs `Examples`, `Examples on Python 3.14`) | deterministic; a machine of their own in CI |
| Speed tests (marked `benchmark`) | full run only | — | fail on a busy machine |
| Build wheel/sdist × 7, packaging smoke | — | ✅ | need the network; matter at a release |
| Graph files: write | ✅ (green run only) | — | writes files into the commit |
| Graph files: check | ✅ (always) | ✅ (always) | never skipped |
| Versions grew | — | ✅ (pull requests into `main`) | compares a pull request with `main`; see [Versions](#versions) |

CI runs on every pull request, in parallel jobs: `Checks`, `Checks on Python 3.14`, `Examples`, `Examples on Python 3.14`, `Packaging`, and `Versions` on a pull request into `main`. Your machine, `Checks` and `Examples` use the version in `.python-version`, 3.12; the two `on Python 3.14` jobs run the same steps on the newest version the project supports. The examples have jobs of their own because jobs run at the same time on separate machines: a pull request waits for the longest job, not for all of them in a row. Each job calls the same runner:

```bash
bash scripts/run_checks_with_log.sh --where ci --skip-group packaging --skip-group examples   # both Checks jobs
bash scripts/run_checks_with_log.sh --where ci --only-group examples   # both Examples jobs
bash scripts/run_checks_with_log.sh --where ci --only-group packaging   # the Packaging job
```

`Checks` also runs `graph-builder`'s own action from gnomon, the one every project uses, at the Maxitor release this repository takes.

## Versions

[`version-gate`](https://github.com/bystrovmaxim/version-gate) fails a pull request into `main` when a level it changed did not raise its version. It runs only in CI, because it compares with `main`. A folder is a level when it holds a `version.toml`:

| Level | Folders | Where the number is |
|---|---|---|
| Repository | the root | root `pyproject.toml`; `require_bump = false`, so it need not grow |
| Package | the seven `aoa-*` packages | their `pyproject.toml` |

A change raises the version of every level it lies in, apart from the repository; the job names each level whose version did not grow, with the version it has and the one on `main`. Raise them, commit, and the job passes. A sub-issue merging into a feature branch is not checked, so a large task raises its versions once, on its way into `main`.

Some files do not count: changelogs, tests, examples, and the READMEs of the `aoa-*` packages. The list is `[changes] ignore` in the root `version.toml`, and a new pattern works only after it is merged. The protocol's frozen schemas in `packages/open-gnomon-protocol/graph/` are no level: they never change here.

## Ruff

There is one Ruff step, `Ruff auto-fix`. On your machine, in a full run, it runs `ruff check --fix`: it fixes what it can and fails on what is left. In CI, which must not change the tree, it runs `ruff check` and fails on any finding.

An error Ruff cannot fix, such as an undefined name, fails everywhere:

```text
FAIL Ruff auto-fix (exit 1, 0.1 s)
```

An error Ruff can fix, such as an unused import, is fixed on your machine and the step passes. The fix is part of your change, so commit it:

```text
OK Ruff auto-fix (exit 0, 0.1 s)
```

The same error fails in CI and the file stays as it was, so a pull request with something unfixed does not pass:

```bash
bash scripts/run_checks_with_log.sh --where ci --only-group first
```

```text
FAIL Ruff auto-fix (exit 1, 0.1 s)
```

## Complexity and maintainability

The two Radon steps fail the run. `Radon cyclomatic complexity` fails on any function graded D or worse, which is a complexity of 21 and above. `Radon maintainability index` fails on any module graded B or worse, which is an index of 19 and below. Both read `packages/`, tests included, and run in every context. Run one on its own:

```bash
uv run --extra dev task cc
uv run --extra dev task mi
```

Nothing over the limit, exit 0:

```text
1253 files read, over the limit: 0.
```

A function over the limit, exit 1. Every offender is listed, not only the first:

```text
packages/aoa-demo/src/aoa/demo/example.py:1 heavy — grade D (complexity 21)
packages/aoa-demo/src/aoa/demo/example.py:43 heavy_two — grade D (complexity 21)
2 finding(s) in 1254 files.
```

A module over the limit, exit 1:

```text
packages/aoa-demo/src/aoa/demo/example.py — grade B (index 11.45)
1 finding(s) in 1488 files.
```

A file Radon cannot parse fails the step too, and so does a report that cannot be read at all, so a broken tool never looks like a clean tree:

```text
packages/aoa-demo/src/aoa/demo/example.py — Radon could not read it: invalid syntax (<unknown>, line 1)
1 finding(s) in 1254 files.
```

Simplify what is over the limit. When that is not reasonable, add an exception with its reason to `scripts/check_radon.py`:

```python
# (file, name) to why it stays; a method is named ``Class.method``.
FUNCTION_EXCEPTIONS: dict[tuple[str, str], str] = {
    ("packages/aoa-demo/src/aoa/demo/example.py", "heavy"): "One flat table of cases; splitting it hides the table.",
}
# File to why it stays.
MODULE_EXCEPTIONS: dict[str, str] = {}
```

The step then passes, and its log names the exception.

```text
excepted: packages/aoa-demo/src/aoa/demo/example.py heavy — One flat table of cases; splitting it hides the table.
1254 files read, over the limit: 0.
```

Exceptions cannot outlive what they excuse. Once the function is simplified or gone, the step fails:

```text
packages/aoa-demo/src/aoa/demo/example.py heavy — stale exception: not over the limit any more
1 finding(s) in 1253 files.
```

An exception with an empty reason excuses nothing, and fails as well:

```text
packages/aoa-demo/src/aoa/demo/example.py:1 heavy — grade D (complexity 21)
packages/aoa-demo/src/aoa/demo/example.py heavy — exception has no reason
2 finding(s) in 1254 files.
```

## Examples

`Examples: scripts, notebooks, pages, links` checks every example a reader can run, in parallel: about a minute on a developer's machine, a few minutes in CI's `Examples` jobs, which leave the tree as it was:

```bash
uv run --extra dev pytest tests/examples -n auto -q
```

| What | What passes |
|---|---|
| A script of `examples/` | it runs from the repository root and exits with 0; nothing is skipped or expected to fail. A folder with `__init__.py` is a package an example imports, not an example |
| A `Result` a script builds | it reads back from its own JSON with the same observable state: the script runs through `tests/examples/round_trip_runner.py`, which names the `Result` and the first difference ([what goes out comes back in](authoring-action.md#what-goes-out-comes-back-in)) |
| A notebook of `examples/` | there is one beside every script; it runs in a fresh kernel in its own folder; every line it prints is a line its script prints, in the same order. The kernel talks over Unix sockets rather than TCP ports, so kernels started in parallel never take each other's ports |
| The notebook's first code cell | `!pip install …`, naming every package its imports need by its PyPI name, so it opens in Colab as it is |
| A Python block of a page | it runs as written, or its first line says why it does not |
| The output a page shows | it is what the block before it prints |
| A link to an example | the file exists; a Colab button opens the repository's notebook |

Values that differ on every run — ids, times, durations, ports, tokens, the Pydantic version in an error link — are masked before anything is compared.

**A block that does not run on its own** starts with a fragment mark and its reason:

```text
# Fragment: its imports are left out.
```

Such a block is not run. Every other Python block of a page runs after the earlier ones of the same page, in one process from the repository root, so a chapter can build one example over several blocks. A block that opens with a docstring is a whole module and runs in a process of its own.

**An output a page shows** is a `text` block, or a block with no language, right after a Python block, with nothing between them or one lead-in sentence that ends with a colon. Any other prose between them breaks the pair.

**A Colab button** points at the repository, never at a copy:

```text
[▶ Try in Colab](https://colab.research.google.com/github/bystrovmaxim/aoa/blob/main/examples/step_01_Action_and_pipeline/01_hello_world.ipynb)
```

**A notebook's install cell** is checked against its imports through one table, `PYPI_FOR_MODULE` in `tests/examples/harness.py`; a module the table does not know fails the check until it is added there.

## Secrets

`scripts/check_no_secrets.py` fails on a tracked `.env`, `.env.*`, `*.pem` or `*.key`, whatever it holds, and on any value `detect-secrets` finds that `.secrets.baseline` does not list. `.env.example` is allowed. Tests under the root `tests/`, `docs/`, `archive/`, `specs/`, `.specify/integrations/`, notebooks and `graph.json` files are not scanned, because their text is full of sample values and hashes.

The same check runs as a commit hook, once per checkout:

```bash
uvx pre-commit install
```

A failure names the file and the kind of finding, and never prints the value:

```text
FAIL .env is a secrets file and must not be tracked: git rm --cached .env
FAIL scripts/check_run.py: Secret Keyword. Remove it, or if it is a false alarm, review it and run --update.
```

After reviewing a false alarm, record it. The baseline is compared by file, kind and hash, so moving a reviewed value to another line does not fail the check:

```bash
uv run --extra dev python scripts/check_no_secrets.py --update
```

## Before a pull request

CI runs the closing check run on every pull request, so a pull request needs nothing from your machine: open it whole, and it merges when CI is green. The full local run is there when you want the answer before CI gives it.

## The limit, and running one step at a time

At most as many steps run at once as the machine has cores. `AOA_CHECK_JOBS` changes that; `1` runs one step at a time — the guards and the auto-fix first, then the rest in the table's order — and the log is the same as with any other limit:

```bash
AOA_CHECK_JOBS=1 bash scripts/run_checks_with_log.sh
```

```text
Full check run (cwd=/Users/bystrovmaxim/PythonDev/aoa, up to 1 step at once)...

> Ban __getattr__ in package __init__.py
OK Ban __getattr__ in package __init__.py (exit 0, 0.4 s)
> Ruff auto-fix
OK Ruff auto-fix (exit 0, 0.1 s)
> Mypy typecheck
…
```

One step at a time takes several times longer. Use it when the machine is busy with something else, or to see a step's speed without others beside it.

A limit that is not a positive whole number stops the run before any step, with exit code 2:

```bash
AOA_CHECK_JOBS=0 bash scripts/run_checks_with_log.sh
```

```text
FAIL AOA_CHECK_JOBS must be a positive whole number, got '0'.
```

## When a step fails

A failing step does not stop the others: every step still runs and reports, and the run exits 1. Here a package's `__init__.py` defined `__getattr__`; the console shows the guard's failure among the others:

```text
FAIL Ban __getattr__ in package __init__.py (exit 1, 0.4 s)
OK Ruff auto-fix (exit 0, 0.1 s)
```

To find every failure in the log and read it, look for the `FAIL` lines; the step's block starts at its `===` line:

```bash
grep -n "^FAIL" archive/logs/check-all.txt
```

```text
13:FAIL Ban __getattr__ in package __init__.py (exit 1, 0.4 s)
```

The block above that line holds the step's own report:

```text
=== Ban __getattr__ in package __init__.py ===
$ check_no_lazy_init_getattr (shell function)

Forbidden package-level lazy export found: __getattr__ in __init__.py
packages/aoa-otel/src/aoa/otel/__init__.py:29:def __getattr__(name):
FAIL Ban __getattr__ in package __init__.py (exit 1, 0.4 s)
```

## Stopping a run

Ctrl+C stops every running step, together with whatever it started — servers, test processes, notebook kernels — and the run exits 130. The log then holds the steps that had ended, and ends with `Run interrupted` instead of `All steps finished`:

```text
OK Radon maintainability index (exit 0, 9.6 s)

Wall time: 12.2 s
Log: /Users/bystrovmaxim/PythonDev/aoa/archive/logs/check-all.txt
Run interrupted
```

```text
==================================================
Run interrupted
Wall time: 12.2 s
Log: /Users/bystrovmaxim/PythonDev/aoa/archive/logs/check-all.txt
==================================================
```

An interrupted run is not a green run: start it again before calling a change finished.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | every step passed |
| 1 | at least one step failed; every step still ran and reported |
| 2 | the run did not start: the limit is not a positive whole number, or the repository has no `pyproject.toml` |
| 130 | interrupted; no step is left running |

