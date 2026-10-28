# Research: A Check Run That Measures Itself and Runs Independent Steps Together

Decisions for [spec.md](spec.md), checked against the repository and the maintainer's machine on 2026-10-28.

## R1. What runs the steps

- **Decision**: `bash scripts/run_checks_with_log.sh` stays the one entry point (the constitution names it). It checks it is in the repository and hands over to a new runner, `scripts/check_run.py`, written with Python's standard library only and started with `uv run --extra dev python scripts/check_run.py "$@"`. The runner holds the step table, starts the steps, times them, limits how many run at once, stops them on interrupt and writes the log.
- **Rationale**: `bash` on macOS is **3.2.57** — the one the maintainer's `bash` resolves to. It has no `wait -n` (wait for whichever job ends first), no associative arrays and no sub-second clock, so a job limit, dependencies between steps and per-step timing in it would mean polling loops and `date` tricks that differ between systems. The runner gets a monotonic clock, process groups for a clean interrupt and a plain table of steps that reads as data. Ruff already lints `scripts/`, so the runner is checked like the other scripts there. Starting it through `uv run --extra dev` prepares the project's environment **once, before any step**, so parallel steps do not race to prepare it.
- **Alternatives considered**:
  - Bash with background jobs and a polling loop. Rejected: every one of the problems above, and no way to test it short of running it.
  - `xargs -P` or GNU `parallel`. Rejected: neither expresses "after the client build" or "never during the client build", and `parallel` is not installed by default.
  - Requiring bash 5 from Homebrew. Rejected: the check run must work with the system's `bash`.

## R2. The step table

- **Decision**: one ordered table of the 37 steps, in today's order, with today's names and today's commands, each with its group and the steps it must wait for. The two shell guards keep their functions in `run_checks_with_log.sh`; the runner calls them as `bash scripts/run_checks_with_log.sh --guard <name>`, and their log blocks keep today's command line (`$ check_no_lazy_init_getattr (shell function)`).
- **Rationale**: FR-001 — the same checks, the same commands; the table is the single place to read what runs and in which order, and the log order comes from it.
- **Alternatives considered**: porting the guards to Python. Rejected: it changes two checks, which this issue does not do.

## R3. What may run at the same time

- **Decision**:

  | Group | Steps | Waits for |
  |---|---|---|
  | First, alone | the two guards, then `ruff check --fix` | — (in order, nothing else runs) |
  | Client | build; then unit tests, the three-engine layout step, five ERD scripts | the build, for every step after it |
  | Static analysis | Ruff lint, mypy, pylint, package boundaries, package metadata, vulture, samples public API, Radon cc, Radon mi | ruff `--fix` |
  | Packaging | eight package builds; then the packaging smoke test | ruff `--fix`; the Maxitor build also waits for the client build; the smoke test waits for all eight builds |
  | Tests | pytest for each of the eight packages | ruff `--fix` |

  Groups run beside each other under one limit (R4).
- **Rationale**: These are exactly the dependencies found in the code (spec "Context"): `ruff --fix` rewrites Python files; the client steps read `client/dist`; the Maxitor sdist packs `client/` including `client/dist`; each build writes only its own `packages/<pkg>/dist`, and the smoke test reads all of them. The eight builds may therefore run beside each other — #279 put them in order only because it assumed one shared `dist/`, which is not the case.
- **Alternatives considered**: the builds strictly in order, as #279 drafted. Kept as the fallback if phase 4 finds that two builds disturb each other.

## R4. The limit

- **Decision**: the environment variable `AOA_CHECK_JOBS` sets how many steps may run at once; its default is the number of cores (`os.cpu_count()`, 14 on the maintainer's M3 Max). A value that is not a positive whole number stops the run before any step, with a message naming the variable and the value. `AOA_CHECK_JOBS=1` runs the table in order.
- **Rationale**: FR-008. A step is one unit whatever it does inside; pylint already runs on all cores itself (`jobs = 0` in `pyproject.toml`), and the measurements of phases 1 and 5 decide whether the default needs lowering — not a guess now.

## R5. Output, timing and the log

- **Decision**: each step writes its standard output and error into its own file in a temporary folder. The console prints `> <name>` when a step starts and `OK <name> (exit 0, 12.3 s)` or `FAIL <name> (exit N, 12.3 s)` when it ends, in the order they end. When every step has ended, the runner writes `check-all.txt`: today's header, then one block per step **in table order**, then today's footer and the total wall time. A block reads as today — `=== <name> ===`, `$ <command>`, a blank line, the full output, a blank line, the `OK`/`FAIL` line — with the duration added to that line. Durations come from a monotonic clock, to a tenth of a second.
- **Rationale**: FR-002 – FR-004: the log is joined after the fact, so outputs cannot interleave, and a run with one job reads exactly like one with fourteen apart from times.
- **Alternatives considered**: writing to the log as steps end. Rejected: the order of the log would then depend on timing.

## R6. Failure and interrupt

- **Decision**: a failing step marks itself `FAIL` and the others go on; steps that wait for a failed step still run (the client steps after a failed build fail on their own and say why), so every step reports. The run exits 1 if any step failed, 0 otherwise. Each step runs in its own process group; on Ctrl+C or a termination signal the runner sends every running group a termination signal, waits up to five seconds, kills what is left, writes the log of what finished followed by `Run interrupted`, and exits 130.
- **Rationale**: FR-009, FR-010; process groups reach the grandchildren (`npm`, `uv`, the layout step's own API server).
- **Alternatives considered**: skipping the steps that wait for a failed step. Rejected: FR-009 wants every step to report, and today a failed build does not stop the steps after it either.

## R7. How the runner itself is verified

- **Decision**: no new check step is added (FR-001; #279 §6.1), so the runner is verified the way #279's acceptance criteria say: the per-step times and the joined log are compared with a log from before (phases 1–2); the breaks of User Story 3 — one failing step in each group, Ctrl+C, a limit of 1, an invalid limit — are run and recorded; ten parallel runs in a row are green (phase 4). Ruff lints the runner in every check run.
- **Rationale**: a unit-test suite for the runner would need a check step to run it, which this issue may not add. If the maintainer wants one, it is a follow-up.

## R8. Tests that may disturb each other

- **Decision**: phase 4 runs the eight pytest steps in parallel ten times on a clean tree. Looked at in advance: the JWT test binds port 0 (a free one); the Maxitor integration test that needs a service on port 8001 is skipped; the demo's Postgres tests use their own fake unless a DSN is set. No fixed port or shared file is known today, so phase 4 is expected to confirm rather than fix — it is still run, because a timing limit can fail only under load.

## R9. The phases

The six phases of #279, each one commit except the tail:

1. **The runner, sequential, with times.** `check_run.py` with the table and `AOA_CHECK_JOBS` fixed at 1 in effect; the log as today plus durations and total time. Two timed runs posted on #279 as the baseline. (#279 phase 1 — moving to the runner here rather than adding timing to bash first, because bash 3.2 has no sub-second clock and the bash version would be thrown away in phase 3.)
2. **One output file per step, joined in order.** Still sequential; the log reads as phase 1's.
3. **Groups and the limit**, with interrupt handling (R3, R4, R6).
4. **Tests that do not share anything** (R8).
5. **Measure and decide** (FR-012): two parallel runs beside the baseline; ship only if green and faster.
6. **The tail**: check run, documentation, changelog.

## R10. Documentation

- **Decision**: a new how-to page, `docs/how-to/run-the-checks.md`, with each case as a command and what it printed: a normal run and how to read its log, a failure, a limit of 1, an invalid limit, an interrupt; `AGENTS.md` and the constitution's wording stay as they are (the command does not change). The Russian draft beside the page.
- **Decided by the maintainer (2026-10-28)**: the how-to page with each case as its command and what it printed is enough; no `examples/` script and no notebook (Principle VI.5 is answered in the plan's Constitution Check).
