# scripts/check_run.py
"""
Check run — every step of the repository's check run, timed, with one log.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``bash scripts/run_checks_with_log.sh`` hands over to this runner. It holds the
table of every step the check run executes — today's names and today's commands,
in today's order — runs them, times each one, prints ``OK`` or ``FAIL`` with the
duration, and writes ``archive/logs/check-all.txt``. The run exits 1 if any step
failed and 0 otherwise; a failing step never stops the others.

Each step writes into its own file; when every step has ended, the log is joined
from those files in the table's order, so it never depends on which step ended
first and two steps' output never mix.

Steps run side by side where nothing forbids it. The two shell guards and
``ruff check --fix`` run first, in order and alone, because the auto-fix rewrites
files every later Python step reads; then every step starts as soon as the steps
it waits for (``after``) have ended and none it must not overlap (``not_during``)
is running, as long as fewer than the limit are running. The limit is
``AOA_CHECK_JOBS`` (default: the number of cores); ``AOA_CHECK_JOBS=1`` runs one
step at a time with the same log. Ctrl+C stops every running step: each one runs
in its own process group, so the signal reaches what it started too.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    run_checks_with_log.sh  ──exec──►  check_run.py
                                           │
             STEPS ── after / not_during / AOA_CHECK_JOBS ──► ready steps
                                           ▼
                 bash -c <command>  ──output──►  <temporary folder>/<NN>.out
                       │                                     │ all steps ended
                       └──► console: > name / OK|FAIL        ▼ table order
                                                  archive/logs/check-all.txt

Python's standard library only: the runner starts before anything is installed
or built, and must not depend on what it checks.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LOG_FILE = REPO_ROOT / "archive" / "logs" / "check-all.txt"

RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
NC = "\033[0m"

CLIENT = "cd packages/aoa-maxitor/client"
AUTO_FIX = "Ruff auto-fix"
LAZY_GUARD = "Ban __getattr__ in package __init__.py"
README_GUARD = "Maxitor client: README beside components/*/ index.ts"
JOBS_VARIABLE = "AOA_CHECK_JOBS"
STOP_GRACE_SECONDS = 5.0
POLL_SECONDS = 0.05
CLIENT_BUILD = "Maxitor client: npm ci and Vite build"
PACKAGES = (
    "packages/aoa-action-machine",
    "packages/aoa-ocel",
    "packages/aoa-otel",
    "packages/aoa-fastapi-adapter",
    "packages/aoa-mcp-adapter",
    "packages/aoa-langgraph",
    "packages/aoa-maxitor",
    "packages/aoa-demo",
)


@dataclass(frozen=True)
class Step:
    """
    AI-CORE-BEGIN
    ROLE: One step of the check run: what it is called, what it runs, and what it must wait for.
    CONTRACT: ``command`` runs through ``bash -c`` from the repository root; ``shown`` is the command line the log prints, ``command`` when empty.
    INVARIANTS: ``name`` is unique in ``STEPS``; ``after`` and ``not_during`` name other steps of the table; the table's order is the log's order.
    AI-CORE-END
    """

    name: str
    command: str
    group: str
    after: tuple[str, ...] = ()
    not_during: tuple[str, ...] = ()
    shown: str = ""
    blank_before_result: bool = True

    @property
    def log_command(self) -> str:
        """The command line the log shows for this step."""
        return self.shown or self.command


def _guard(name: str, guard: str, function: str, after: tuple[str, ...] = ()) -> Step:
    """A shell guard, run by the entry script and logged as it always was: no blank line before its result."""
    return Step(
        name=name,
        command=f"bash scripts/run_checks_with_log.sh --guard {guard}",
        group="first",
        after=after,
        shown=f"{function} (shell function)",
        blank_before_result=False,
    )


def _client(name: str, command: str) -> Step:
    """A client step that uses what the client build wrote."""
    return Step(name=name, command=f"({CLIENT} && {command})", group="client", after=(CLIENT_BUILD,))


def _build(package: str) -> Step:
    """The wheel and sdist build of one package; Maxitor's sdist packs the client, so it waits out the client build."""
    return Step(
        name=f"Build wheel/sdist ({package})",
        command=f'uv run --group dev python -m build "{REPO_ROOT}/{package}"',
        group="packaging",
        after=(AUTO_FIX,),
        not_during=(CLIENT_BUILD,) if package == "packages/aoa-maxitor" else (),
    )


def _after_fix(name: str, command: str, group: str) -> Step:
    """A step that reads files ``ruff --fix`` may have rewritten."""
    return Step(name=name, command=command, group=group, after=(AUTO_FIX,))


STEPS: tuple[Step, ...] = (
    _guard(LAZY_GUARD, "lazy-init-getattr", "check_no_lazy_init_getattr"),
    _guard(README_GUARD, "client-component-readmes", "check_maxitor_client_component_readmes", after=(LAZY_GUARD,)),
    # Two remarks in this log are known, accepted and not to be acted on — they belong to tools,
    # not to this repository's code:
    #   * the Vite build's "Some chunks are larger than 500 kB" — the viewer's weight is the graph
    #     engine and the Graphviz wasm behind layout, and the advisory is about their size;
    #   * LangGraph's `LangChainPendingDeprecationWarning` while its cache module is imported —
    #     raised inside the library, and this repository never builds that cache.
    # Do not chase either one; the steps below stay green with them in the log.
    Step(CLIENT_BUILD, f"({CLIENT} && npm ci && npm run build)", "client", after=(AUTO_FIX,)),
    _client("Maxitor client: unit tests", "npm test"),
    # Every diagram must be laid out to the same bits in Chromium, Firefox and WebKit, on a phone and a
    # desktop screen, or pointers in a room land on the wrong nodes (spec 028, FR-006). The same step
    # then opens a room in each engine and proves a pointer lands within 2 px of its node (SC-003).
    _client(
        "Maxitor client: the same layout in three engines",
        "npx playwright install chromium firefox webkit && node scripts/check-layout-determinism.ts",
    ),
    _client("Maxitor client: ERD card containment", "node scripts/check-erd-card-containment.ts"),
    _client("Maxitor client: dictionary value properties", "node scripts/check-erd-dictionary-values.ts"),
    _client("Maxitor client: group label composed once", "node scripts/check-erd-group-label.ts"),
    _client("Maxitor client: ERD kinds, tables and lines", "node scripts/check-erd-kinds-and-lines.ts"),
    _client("Maxitor client: ERD table style", "node scripts/check-erd-table-style.ts"),
    # The auto-fix step takes the same scope as the lint target below (`task lint`), so that the two
    # agree on what this repository lints. `examples/` and its notebooks are tutorial material and sit
    # outside that scope; while the step scanned everything (`.`) it reported 207 findings inside
    # `examples/` — 162 fixable (import order, unused imports) and 45 `module-import-not-at-top` — none
    # of them introduced by the change that found this and all of them predating it. Widening the scope
    # back to `.` is one line, and it re-opens that debt deliberately.
    Step(
        AUTO_FIX,
        "uv run --extra dev ruff check --fix packages/ tests/ scripts/ aoa_run/",
        "first",
        after=(README_GUARD,),
    ),
    _after_fix("Ruff lint", "uv run --extra dev task lint", "static"),
    _after_fix("Mypy typecheck", "uv run --extra dev task typecheck", "static"),
    _after_fix("Pylint", "uv run --extra dev task pylint", "static"),
    _after_fix(
        "Package import boundaries (production)",
        "uv run --extra dev python scripts/check_package_boundaries.py",
        "static",
    ),
    _after_fix(
        "Package metadata (pyproject dependency matrix)",
        "uv run --extra dev python scripts/check_package_metadata.py",
        "static",
    ),
    *(_build(package) for package in PACKAGES),
    Step(
        "Packaging wheel install smoke",
        "uv run --extra dev pytest tests/packaging -v",
        "packaging",
        after=tuple(f"Build wheel/sdist ({package})" for package in PACKAGES),
    ),
    _after_fix("Vulture dead code", "uv run --extra dev task dead", "static"),
    _after_fix("Maxitor samples: action_machine public API", "uv run --extra dev task samples-public-api", "static"),
    *(
        _after_fix(f"Pytest {package}", f"uv run --extra dev pytest packages/{package}/tests/ -v", "tests")
        for package in (
            "aoa-maxitor",
            "aoa-demo",
            "aoa-otel",
            "aoa-langgraph",
            "aoa-ocel",
            "aoa-fastapi-adapter",
            "aoa-mcp-adapter",
            "aoa-action-machine",
        )
    ),
    _after_fix("Radon cyclomatic complexity", "uv run --extra dev task cc", "static"),
    _after_fix("Radon maintainability index", "uv run --extra dev task mi", "static"),
)


@dataclass(frozen=True)
class Result:
    """
    AI-CORE-BEGIN
    ROLE: What one step left behind: its exit code, how long it took and where its output is.
    CONTRACT: ``exit_code`` 0 is ``OK``, anything else ``FAIL``; ``seconds`` is wall time from a monotonic clock; ``output`` holds everything the step wrote.
    AI-CORE-END
    """

    exit_code: int
    seconds: float
    output: Path

    @property
    def ok(self) -> bool:
        """Whether the step passed."""
        return self.exit_code == 0

    def line(self, name: str) -> str:
        """The step's ``OK``/``FAIL`` line, with its exit code and duration."""
        word = "OK" if self.ok else "FAIL"
        return f"{word} {name} (exit {self.exit_code}, {self.seconds:.1f} s)"


def _say(colour: str, text: str) -> None:
    """Print one console line in a colour, as the entry script always did."""
    print(f"{colour}{text}{NC}", flush=True)


def _header() -> str:
    """The log's header, as it always read."""
    now = datetime.now().astimezone()
    return (
        "==================================================\n"
        "ActionMachine project checks\n"
        f"Date: {now.strftime('%a %b %d %H:%M:%S %Z %Y')}\n"
        f"Time: {now.strftime('%H:%M:%S')}\n"
        f"Repository: {REPO_ROOT}\n"
        "==================================================\n"
        "\n"
    )


@dataclass
class _Running:
    """A step that has started and not yet ended."""

    step: Step
    process: subprocess.Popen[bytes]
    output: Path
    started: float


def _start(step: Step, output: Path) -> _Running:
    """Start one step from the repository root in its own process group, its output going into ``output``."""
    _say(YELLOW, f"> {step.name}")
    with output.open("wb") as handle:
        process = subprocess.Popen(
            ["bash", "-c", step.command],
            cwd=REPO_ROOT,
            stdout=handle,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    return _Running(step=step, process=process, output=output, started=time.monotonic())


def _ready(step: Step, ended: set[str], running: list[_Running]) -> bool:
    """Whether ``step`` may start now: what it waits for has ended, and nothing it must not overlap is running."""
    running_names = {item.step.name for item in running}
    if not set(step.after) <= ended:
        return False
    if running_names & set(step.not_during):
        return False
    return not any(step.name in item.step.not_during for item in running)


def _stop(running: list[_Running]) -> None:
    """Stop every running step and whatever it started: terminate, wait a little, then kill."""
    for item in running:
        _signal_group(item.process, signal.SIGTERM)
    deadline = time.monotonic() + STOP_GRACE_SECONDS
    while any(item.process.poll() is None for item in running) and time.monotonic() < deadline:
        time.sleep(POLL_SECONDS)
    for item in running:
        _signal_group(item.process, signal.SIGKILL)
        item.process.wait()


def _signal_group(process: subprocess.Popen[bytes], sig: signal.Signals) -> None:
    """Send ``sig`` to the process group of ``process``, if it still exists."""
    try:
        os.killpg(process.pid, sig)
    except ProcessLookupError:
        pass


def _run_all(folder: Path, jobs: int, results: dict[str, Result]) -> None:
    """Run every step under the limit, recording in ``results`` each step as it ends."""
    pending = list(STEPS)
    running: list[_Running] = []
    try:
        while pending or running:
            for step in list(pending):
                if len(running) >= jobs:
                    break
                if _ready(step, set(results), running):
                    pending.remove(step)
                    running.append(_start(step, folder / f"{STEPS.index(step):02d}.out"))
            for item in list(running):
                exit_code = item.process.poll()
                if exit_code is None:
                    continue
                running.remove(item)
                result = Result(exit_code=exit_code, seconds=time.monotonic() - item.started, output=item.output)
                results[item.step.name] = result
                _say(GREEN if result.ok else RED, result.line(item.step.name))
            time.sleep(POLL_SECONDS)
    except KeyboardInterrupt:
        _stop(running)
        raise


def _jobs() -> int:
    """The limit from ``AOA_CHECK_JOBS``, or the number of cores; refuse anything but a positive whole number."""
    raw = os.environ.get(JOBS_VARIABLE)
    if raw is None:
        return os.cpu_count() or 1
    if not raw.isdigit() or int(raw) < 1:
        raise ValueError(f"{JOBS_VARIABLE} must be a positive whole number, got {raw!r}.")
    return int(raw)


def _write_log(header: str, results: dict[str, Result], wall: float, interrupted: bool) -> None:
    """Join the blocks of the steps that ended, in table order, between the header and the footer."""
    with LOG_FILE.open("wb") as log:
        log.write(header.encode())
        for step in STEPS:
            result = results.get(step.name)
            if result is None:
                continue
            log.write(f"=== {step.name} ===\n$ {step.log_command}\n\n".encode())
            log.write(result.output.read_bytes())
            gap = "\n" if step.blank_before_result else ""
            log.write(f"{gap}{result.line(step.name)}\n\n".encode())
        ending = (
            "Run interrupted"
            if interrupted
            else "All steps finished (see FAIL lines above or in the log if anything failed)"
        )
        log.write(
            "==================================================\n"
            f"{ending}\n"
            f"Wall time: {wall:.1f} s\n"
            f"Log: {LOG_FILE}\n"
            "==================================================\n".encode()
        )


def _raise_interrupt(signum: int, frame: object) -> None:
    """Turn a termination signal into the same stop as Ctrl+C."""
    del signum, frame
    raise KeyboardInterrupt


def main() -> int:
    """Run every step under the limit and return the run's exit code."""
    try:
        jobs = _jobs()
    except ValueError as refusal:
        _say(RED, f"FAIL {refusal}")
        return 2
    signal.signal(signal.SIGTERM, _raise_interrupt)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    _say(YELLOW, f"Log file: {LOG_FILE}")
    print()
    header = _header()
    steps = "step" if jobs == 1 else "steps"
    _say(YELLOW, f"Full check run (cwd={REPO_ROOT}, up to {jobs} {steps} at once)...")
    print()
    started = time.monotonic()
    interrupted = False
    results: dict[str, Result] = {}
    with tempfile.TemporaryDirectory(prefix="check-run-") as name:
        try:
            _run_all(Path(name), jobs, results)
        except KeyboardInterrupt:
            interrupted = True
        wall = time.monotonic() - started
        _write_log(header, results, wall, interrupted)
    print()
    _say(YELLOW, f"Wall time: {wall:.1f} s")
    _say(GREEN, f"Log: {LOG_FILE}")
    if interrupted:
        _say(RED, "Run interrupted")
        return 130
    return 0 if all(result.ok for result in results.values()) else 1


if __name__ == "__main__":
    os.chdir(REPO_ROOT)
    sys.exit(main())
