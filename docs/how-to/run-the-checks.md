# Run the checks

No change in this repository is finished until the check run is green. Two scripts name the moments, and they run from anywhere inside the repository:

```bash
bash scripts/check_before_commit.sh   # during the work and before every commit
bash scripts/check_before_pr.sh       # on the pushed commit, before a pull request
```

The first runs the cheap steps. The second runs only what CI cannot run, the browsers, and leaves its proof on the commit, where CI reads it. Under both lies one command, which is the full gate on its own, for when you want everything on your machine:

```bash
bash scripts/run_checks_with_log.sh
```

It runs two repository guards, Ruff, mypy, pylint, the package-boundary and package-metadata checkers, the secrets check, vulture, the samples public-API check, the Maxitor client's build and its tests (including the layout in three browser engines), the five ERD scripts, the tests of every package, Radon, and a check of the saved graph files — and writes everything they print into one log, `archive/logs/check-all.txt`. The wheel and sdist build and the packaging smoke test are **not** part of the local run: they need the network and matter when a package is released, so CI runs them. Once the tools are installed — Graphviz's `sfdp` among them, for the map — the run needs no network. Steps that do not depend on each other run at the same time, so the run takes about as long as its slowest chain of steps instead of the sum of all of them.

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
OK Pytest aoa-action-machine (exit 0, 52.7 s)
OK Pytest maxitor/front (exit 0, 70.3 s)
OK Maxitor client: npm ci and Vite build (exit 0, 208.2 s)
OK Maxitor client: the same layout in three engines (exit 0, 280.1 s)
> Graph files (graph-builder write)
OK Graph files (graph-builder write) (exit 0, 2.6 s)
> Graph files (graph-builder check)
OK Graph files (graph-builder check) (exit 0, 2.4 s)

Wall time: 494.4 s
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
| Static analysis | Ruff lint, mypy, pylint, package boundaries, package metadata, no secrets in tracked files, vulture, samples public API, Radon | the auto-fix |
| Tests | the tests of each package, one run per package (`maxitor` in two: `maxitor/front` and `maxitor/tools/graph_builder`), and `tests/scripts` (the runner's own last-step rule, the saved graph files) | the auto-fix |
| Only on a green run | `Graph files (graph-builder write)`: builds the repository's graphs and updates their files ([graph_builder](../../packages/maxitor/tools/graph_builder/README.md)) | every other step except the graph check; if any failed, it does not run and its block reads `SKIPPED Graph files (graph-builder write): N step(s) failed` — neither `OK` nor `FAIL` |
| Last, always | `Graph files (graph-builder check)`: verifies the saved graph files are current | the graph write; it runs even when another step failed |

The graph write may change `packages/aoa-demo/graph.json` and `packages/maxitor/front/graph.json`, as the auto-fix may change sources; the run stays green, and the changed files go into the commit with the change that changed the graph. The check comes after it, so a stale file is rewritten on a green run instead of failing it:

```text
OK Graph files (graph-builder write) (exit 0, 3.8 s)
OK Graph files (graph-builder check) (exit 0, 1.9 s)
```

After a failure elsewhere the write is skipped and the check still reports, so the files are never left neither written nor checked. The eight package builds and the packaging smoke test are not in the local table: they run only in CI.

The run is as long as its longest chain, and today that is one chain: the client build and then the three-engine layout step, about 200 + 280 s when everything runs at once. Every other step finishes beside it, so only making this chain shorter makes the run shorter.

### The three-engine layout step

"Maxitor client: the same layout in three engines" serves the built client and a frozen reference graph, starts a Maxitor API of its own, and checks three things in Chromium, Firefox and WebKit:

- **layout hashes** — every page the left panel lists, in every layout mode (61 page-modes), gets the same layout hash in all three engines on a phone-sized (375×812) and a desktop-sized (1600×900) screen;
- **pointer in a room** — in each engine a desktop and a phone page in one room: a resting pointer and a tap land within 2 px of the same node, before and after zooming;
- **following** — in each of the six directed pairs of engines, the follower's screen is centred on the leader's point within 2 px and shows the leader's hover within 500 ms;
- **following on every kind of diagram**, **every change of the picture in one frame** and **the card and collapsing** — the three parts that come after them.

The layout hashes run with both screen sizes at once in every engine, and the pointer cases run beside them; the six following pairs then run at once, each in its own room. The following pairs wait for the rest because their 500 ms hover limit was missed when every browser was open together. The step's output ends with the time of each part:

```text
ok    ERD, all domains | gv-dot-lr  59ddb92209f38108
…
ok    pointer in a room | chromium  largest offset 0.009 px (0.007 / 0.005 / 0.005 / 0.009)
…
ok    following | chromium → firefox  screens apart 0.000 px, hover after 13 ms, circles 4.0 px apart, card buttons overrun 0.0 px
…
part A (layout hashes) 33.2 s
part B (pointer in a room) 11.8 s
part C (following) 7.1 s
part D (following on every diagram) 77.2 s
part E (every change in one frame) 124.6 s
part F (the card and collapsing) 32.9 s
61 page-modes × 3 engines × 2 sizes in 278 s
```

Its lines always come in the same order — pages in the left panel's order, then the pointer cases, then the pairs — whichever part or engine finishes first.

## Where each step runs

Every step has one stated home. The same table in `scripts/check_run.py` drives the local run and every CI job, and each context selects its rows:

| Step | Local run | CI | Why |
|---|---|---|---|
| Ban `__getattr__` in package `__init__.py` | ✅ | ✅ | cheap guard, no network or browser |
| Maxitor client: README beside `components/*/index.ts` | ✅ | ✅ | cheap guard |
| Ruff auto-fix | ✅ | — | rewrites files; CI must not change the tree |
| Ruff lint, mypy, pylint | ✅ | ✅ | deterministic static checks |
| Package boundaries, package metadata | ✅ | ✅ | deterministic static checks |
| No secrets in tracked files | ✅ | ✅ | deterministic; a commit made without the local hook still meets it in CI |
| Vulture, samples public API, Radon | ✅ | ✅ | deterministic static checks |
| Client build, client unit tests, five ERD scripts | ✅ | ✅ | deterministic, no browser engine |
| The same layout in three engines | ✅ | — (CI reads its proof) | needs a graphics card: a CI machine has none, so Firefox has no WebGL |
| Python tests of every package, `tests/scripts` | ✅ | ✅ | deterministic |
| Speed tests (marked `benchmark`) | full run only | — | fail on a busy machine |
| Build wheel/sdist × 8, packaging smoke | — | ✅ | need the network; matter at a release |
| Graph files: write | ✅ (green run only) | — | writes files into the commit |
| Graph files: check | ✅ (always) | ✅ (always) | never skipped |

CI runs on every pull request, in three parallel jobs: `Checks`, `Packaging` and `Proof of the local run`. Each calls the same runner:

```bash
bash scripts/run_checks_with_log.sh --where ci --skip-group packaging   # the Checks job
bash scripts/run_checks_with_log.sh --where ci --only-group packaging   # the Packaging job
python3 scripts/check_run.py --await-sign-off "$COMMIT"                 # the Proof of the local run job
```

`Checks` also runs `graph_builder`'s own action, the one other projects use.

## During the work and before a commit

`check_before_commit.sh` is the full run's `--fast` mode: the guards, the static checks and the Python tests without the speed tests. It skips the client build, the browsers and the graph files. Anything you add to its command line goes on to the run.

A fast run prints only the rows it selected:

```bash
bash scripts/check_before_commit.sh
```

```text
> Ban __getattr__ in package __init__.py
OK Ban __getattr__ in package __init__.py (exit 0, 0.4 s)
> Maxitor client: README beside components/*/ index.ts
OK Maxitor client: README beside components/*/ index.ts (exit 0, 0.1 s)
> Ruff auto-fix
OK Ruff auto-fix (exit 0, 0.2 s)
> Ruff lint
> Mypy typecheck
> Pylint
…
OK Pytest aoa-ocel (exit 0, 3.4 s)
…
Wall time: 66.9 s
```

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

A CI machine has no graphics card, so Firefox has no WebGL there and the map cannot be drawn. The browsers therefore run on your machine, and CI controls that they did. **No pull request is opened until this script has passed on the pushed commit**:

```bash
bash scripts/check_before_pr.sh
```

It runs the client build and the three-engine layout step, about five minutes, and then reports the result to GitHub as the commit status `Local check run`. Everything else CI runs on the pull request, so nothing is checked twice. The speed tests run only when you start the full gate yourself:

```text
…
OK Graph files (graph-builder check) (exit 0, 2.4 s)

Wall time: 494.4 s
Receipt: 35 steps green on c0d3e765. Push it, then: bash scripts/run_checks_with_log.sh --sign-off
OK Local check run on c0d3e765
```

It proves one commit, so it refuses anything else before spending the run. It never commits or pushes:

```text
FAIL the tree has uncommitted changes: a pull request is a commit, so commit them first.
```

```text
FAIL this commit is not pushed: GitHub can only mark a commit it has, so push it first.
```

A red run reports nothing and ends with the run's own exit code. The run also keeps a receipt only when the tree was one commit from start to end. Anything that changes a tracked file during the run changes what was proved, so the run says so, and you commit and run again:

```text
No receipt: the tree was not one commit from start to end. Commit, then run again to sign off.
```

The job `Proof of the local run` reads the status on the pull request's commit. A commit that had its run passes on the first read. A commit pushed to an open pull request gets 15 minutes for its run, so a push does not turn the job red while the run is going. With no proof by then the job fails, and a later run needs that job re-run:

```text
FAIL c0d3e765 has no proof of the full local run: run bash scripts/check_before_pr.sh on it, then re-run this job
```

The merge rule of `main` requires this job, so a new commit cannot merge until it is proved. The status is an attestation, not a proof: anyone with write access could post one.

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

`--sign-off` exits 0 when GitHub took the status and 1 when it refuses or GitHub does; `--await-sign-off` exits 0 once the proof is there and 1 when the wait ends without it.
