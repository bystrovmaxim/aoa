# Run the checks

No change in this repository is finished until the check run is green. It is one command, run from anywhere inside the repository:

```bash
bash scripts/run_checks_with_log.sh
```

It runs 37 steps — two repository guards, the Maxitor client's build and its tests (including the layout in three browser engines), Ruff, mypy, pylint, the package-boundary and package-metadata checkers, a wheel and sdist build of every package and a smoke test that installs them, vulture, the samples public-API check, the tests of every package, and Radon — and writes everything they print into one log, `archive/logs/check-all.txt`. Steps that do not depend on each other run at the same time, so the run takes about as long as its slowest chain of steps instead of the sum of all of them: on an Apple M3 Max with 14 cores, **about 57 s instead of about 220 s**.

This page shows each case as the command and what it really printed.

## A normal run

The console shows each step when it starts (`>`) and when it ends, with its exit code and how long it took. Steps end in whatever order they finish:

```text
Log file: /Users/bystrovmaxim/PythonDev/aoa/archive/logs/check-all.txt

Full check run (cwd=/Users/bystrovmaxim/PythonDev/aoa, up to 14 steps at once)...

> Ban __getattr__ in package __init__.py
OK Ban __getattr__ in package __init__.py (exit 0, 0.4 s)
> Maxitor client: README beside components/*/ index.ts
OK Maxitor client: README beside components/*/ index.ts (exit 0, 0.1 s)
> Ruff auto-fix
OK Ruff auto-fix (exit 0, 0.1 s)
> Maxitor client: npm ci and Vite build
> Ruff lint
…
OK Maxitor client: unit tests (exit 0, 13.5 s)
OK Packaging wheel install smoke (exit 0, 7.7 s)
OK Pytest maxitor/app (exit 0, 39.4 s)
OK Pytest maxitor/tools/graph_builder (exit 0, 6.4 s)
OK Maxitor client: the same layout in three engines (exit 0, 30.1 s)
OK Pytest aoa-action-machine (exit 0, 49.8 s)

Wall time: 57.0 s
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
=== Ruff lint ===
$ uv run --extra dev task lint

All checks passed!

OK Ruff lint (exit 0, 0.1 s)

…
==================================================
All steps finished (see FAIL lines above or in the log if anything failed)
Wall time: 57.0 s
Log: /Users/bystrovmaxim/PythonDev/aoa/archive/logs/check-all.txt
==================================================
```

A block holds only its own step's output, so two steps' lines never mix. Two remarks are known and accepted, and stay in a green run: the Vite build's advice that some chunks are larger than 500 kB, and LangGraph's `LangChainPendingDeprecationWarning`. Both come from the tools, not from this repository's code.

## What runs together and what waits

The steps, their order and what each waits for are one table in `scripts/check_run.py`. The rules come from what the steps read and write:

| Group | Steps | Waits for |
|---|---|---|
| First, alone | the two guards, then `Ruff auto-fix` | nothing; nothing else runs meanwhile, because the auto-fix rewrites files every later Python step reads |
| Client | the client build, then its unit tests, the three-engine layout step and five ERD checks | the auto-fix; everything after the build waits for the build, because it uses what the build wrote |
| Static analysis | Ruff lint, mypy, pylint, package boundaries, package metadata, vulture, samples public API, Radon | the auto-fix |
| Packaging | nine package builds, then the packaging smoke test | the auto-fix; the Maxitor package build never runs during the client build, because its source archive packs the client folder; the smoke test waits for all nine builds |
| Tests | the tests of each package, one run per package (`maxitor` in two: `maxitor/app` and `maxitor/tools/graph_builder`), and `tests/scripts` (the runner's own last-step rule, the saved graph files) | the auto-fix |
| Last, only on a green run | `Graph files (graph-builder write)`: builds the repository's graphs and updates their files ([graph_builder](../../packages/maxitor/tools/graph_builder/README.md)) | every other step; if any failed, it does not run and its block reads `SKIPPED Graph files (graph-builder write): N step(s) failed` — neither `OK` nor `FAIL` |

The last step may change `packages/aoa-demo/graph.json` and `packages/maxitor/app/graph.json`, as the auto-fix may change sources; the run stays green, and the changed files go into the commit with the change that changed the graph. CI only checks them with `graph-builder check`.

The run is as long as its longest chain. Today two chains are almost equal: the client build and then the three-engine layout step (about 22 + 30 s), and the tests of `aoa-action-machine` (about 50 s). Every other step finishes beside them, so making one of these two shorter alone gains only a few seconds.

### The three-engine layout step

"Maxitor client: the same layout in three engines" serves the built client and a frozen reference graph, starts a Maxitor API of its own, and checks three things in Chromium, Firefox and WebKit:

- **layout hashes** — every page the left panel lists, in every layout mode (56 page-modes), gets the same layout hash in all three engines on a phone-sized (375×812) and a desktop-sized (1600×900) screen;
- **pointer in a room** — in each engine a desktop and a phone page in one room: a resting pointer and a tap land within 2 px of the same node, before and after zooming;
- **following** — in each of the six directed pairs of engines, the follower's screen is centred on the leader's point within 2 px and shows the leader's hover within 500 ms.

The layout hashes run with both screen sizes at once in every engine, and the pointer cases run beside them; the six following pairs then run at once, each in its own room. The following pairs wait for the rest because their 500 ms hover limit was missed when every browser was open together. The step's output ends with the time of each part:

```text
ok    ERD, all domains | gv-dot-lr  59ddb92209f38108
…
ok    pointer in a room | chromium  largest offset 0.009 px (0.007 / 0.005 / 0.005 / 0.009)
…
ok    following | chromium → firefox  screens apart 0.000 px, hover after 13 ms, circles 4.0 px apart, card buttons overrun 0.0 px
…
part A (layout hashes) 19.3 s
part B (pointer in a room) 12.2 s
part C (following) 7.1 s
56 page-modes × 3 engines × 2 sizes in 28 s
```

Its lines always come in the same order — pages in the left panel's order, then the pointer cases, then the pairs — whichever part or engine finishes first.

## The limit, and running one step at a time

At most as many steps run at once as the machine has cores. `AOA_CHECK_JOBS` changes that; `1` runs one step at a time — the guards and the auto-fix first, then the rest in the table's order — and the log is the same as with any other limit:

```bash
AOA_CHECK_JOBS=1 bash scripts/run_checks_with_log.sh
```

```text
Full check run (cwd=/Users/bystrovmaxim/PythonDev/aoa, up to 1 step at once)...

> Ban __getattr__ in package __init__.py
OK Ban __getattr__ in package __init__.py (exit 0, 0.4 s)
> Maxitor client: README beside components/*/ index.ts
OK Maxitor client: README beside components/*/ index.ts (exit 0, 0.1 s)
> Ruff auto-fix
OK Ruff auto-fix (exit 0, 0.1 s)
> Maxitor client: npm ci and Vite build
OK Maxitor client: npm ci and Vite build (exit 0, 13.0 s)
> Maxitor client: unit tests
OK Maxitor client: unit tests (exit 0, 7.1 s)
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

A failing step does not stop the others: every step still runs and reports, and the run exits 1. Here a client unit test failed; the console shows it among the others:

```text
FAIL Maxitor client: unit tests (exit 1, 9.5 s)
OK Maxitor client: the same layout in three engines (exit 0, 63.0 s)

Wall time: 86.9 s
```

To find every failure in the log and read it, look for the `FAIL` lines; the step's block starts at its `===` line:

```bash
grep -n "^FAIL" archive/logs/check-all.txt
```

```text
98:FAIL Maxitor client: unit tests (exit 1, 9.5 s)
```

The block above that line holds the test runner's own report:

```text
 FAIL  src/lib/zzBreakOnPurpose.test.ts > fails on purpose
AssertionError: expected 1 to be 2 // Object.is equality
…
 Test Files  1 failed | 29 passed (30)
      Tests  1 failed | 223 passed (224)
…
FAIL Maxitor client: unit tests (exit 1, 9.5 s)
```

## Stopping a run

Ctrl+C stops every running step, together with whatever it started — browsers, servers, test processes — and the run exits 130. The log then holds the steps that had ended, and ends with `Run interrupted` instead of `All steps finished`:

```text
> Maxitor client: the same layout in three engines

Wall time: 25.0 s
Log: /Users/bystrovmaxim/PythonDev/aoa/archive/logs/check-all.txt
Run interrupted
```

```text
==================================================
Run interrupted
Wall time: 25.0 s
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
