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

Every row carries its home: ``local``, ``ci`` or ``both``. The selectors choose
the rows for a context — ``--where local`` (default) keeps ``local`` and ``both``,
``--where ci`` keeps ``ci`` and ``both``, and the narrow selectors (``--only-group``,
``--skip-group``) pick or drop named rows. The local run and every
CI job therefore run the same commands from one table.

Each step writes into its own file; when every step has ended, the log is joined
from those files in the table's order, so it never depends on which step ended
first and two steps' output never mix.

Steps run side by side where nothing forbids it. The shell guard and
``ruff check --fix`` run first, in order and alone, because the auto-fix rewrites
files every later Python step reads (CI runs the same step without ``--fix``, since
it must not change the tree); then every step starts as soon as the steps
it waits for (``after``) have ended and none it must not overlap (``not_during``)
is running, as long as fewer than the limit are running. The limit is
``AOA_CHECK_JOBS`` (default: the number of cores); ``AOA_CHECK_JOBS=1`` runs one
step at a time with the same log. Ctrl+C stops every running step: each one runs
in its own process group, so the signal reaches what it started too.

One step may be marked ``only_if_all_passed``: it starts after every other step
has ended, except the steps that wait for it, and only if all of them passed;
otherwise it is ``SKIPPED`` — neither ``OK`` nor ``FAIL`` — and its block says how
many steps failed. The graph files are written this way: no graph is built for a
run that already failed. They are then *checked* by a step that always runs, after
the write, so a stale file is rewritten on a green run instead of failing it, and
a failure elsewhere never leaves them neither written nor checked.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    run_checks_with_log.sh  ──exec──►  check_run.py
                                           │
             STEPS ── home ──► selector (--where, --only-group, --skip-group)
                                           ▼
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

import argparse
import os
import signal
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LOG_FILE = REPO_ROOT / "archive" / "logs" / "check-all.txt"

RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
NC = "\033[0m"

AUTO_FIX = "Ruff auto-fix"
LAZY_GUARD = "Ban __getattr__ in package __init__.py"
JOBS_VARIABLE = "AOA_CHECK_JOBS"
STOP_GRACE_SECONDS = 5.0
POLL_SECONDS = 0.05
GRAPH_WRITE = "Graph files (graph-builder write)"
# graph-builder from Maxitor 3.22.0, which reads protocol 1.8, taken from gnomon at the commit that merged it: no
# release is needed to move it, only this commit. It runs in an environment of its own, so it never meets this
# repository's workspace packages. CI's graph-builder action is pinned to the same commit.
GRAPH_BUILDER = 'uvx --from "git+https://github.com/bystrovmaxim/gnomon@9ecc198834cc7df462a729f751ddf4870874cc35#subdirectory=packages/maxitor" graph-builder'
PACKAGES = (
    "packages/aoa-action-machine",
    "packages/aoa-ocel",
    "packages/aoa-otel",
    "packages/aoa-fastapi-adapter",
    "packages/aoa-mcp-adapter",
    "packages/aoa-langgraph",
    "packages/aoa-demo",
)
LOCAL = "local"
CI = "ci"
BOTH = "both"


@dataclass(frozen=True)
class Step:
    """
    AI-CORE-BEGIN
    ROLE: One step of the check run: what it is called, what it runs, and what it must wait for.
    CONTRACT: ``command`` runs through ``bash -c`` from the repository root; ``shown`` is the command line the log prints, ``command`` when empty.
    INVARIANTS: ``name`` is unique in ``STEPS``; ``after`` and ``not_during`` name other steps of the table; ``home`` is one of ``local``, ``ci``, ``both``; the table's order is the log's order; ``only_if_all_passed`` waits for every other selected step except those that wait for it, and runs only when all passed; ``ci_command`` replaces ``command`` under ``--where ci``.
    AI-CORE-END
    """

    name: str
    command: str
    group: str
    after: tuple[str, ...] = ()
    not_during: tuple[str, ...] = ()
    shown: str = ""
    blank_before_result: bool = True
    only_if_all_passed: bool = False
    home: str = BOTH
    ci_command: str = ""

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


def _build(package: str) -> Step:
    """The wheel and sdist build of one package, CI only."""
    name = package.rsplit("/", 1)[-1]
    return Step(
        name=f"Build wheel/sdist ({package})",
        command=f"uv build --package {name} --out-dir packages/{name}/dist",
        group="packaging",
        home=CI,
    )


def _after_fix(name: str, command: str, group: str, home: str = BOTH) -> Step:
    """A step that reads files ``ruff --fix`` may have rewritten."""
    return Step(name=name, command=command, group=group, after=(AUTO_FIX,), home=home)


STEPS: tuple[Step, ...] = (
    _guard(LAZY_GUARD, "lazy-init-getattr", "check_no_lazy_init_getattr"),
    # One remark in this log is known, accepted and not to be acted on — it belongs to a library, not to
    # this repository's code: LangGraph's `LangChainPendingDeprecationWarning` while its cache module is
    # imported — raised inside the library, and this repository never builds that cache. Do not chase it;
    # the steps below stay green with it in the log.
    # The only Ruff step: it fixes here, and in CI, which must not change the tree, it
    # only reports. It takes the same scope as `task lint`, so the two agree on what this repository
    # lints. `examples/` and its notebooks are tutorial material and sit
    # outside that scope; while the step scanned everything (`.`) it reported 207 findings inside
    # `examples/` — 162 fixable (import order, unused imports) and 45 `module-import-not-at-top` — none
    # of them introduced by the change that found this and all of them predating it. Widening the scope
    # back to `.` is one line, and it re-opens that debt deliberately.
    Step(
        AUTO_FIX,
        "uv run --extra dev ruff check --fix packages/ tests/ scripts/",
        "first",
        after=(LAZY_GUARD,),
        ci_command="uv run --extra dev ruff check packages/ tests/ scripts/",
    ),
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
    _after_fix("No secrets in tracked files", "uv run --extra dev python scripts/check_no_secrets.py", "static"),
    *(_build(package) for package in PACKAGES),
    Step(
        "Packaging wheel install smoke",
        "uv run --extra dev pytest tests/packaging -v",
        "packaging",
        after=tuple(f"Build wheel/sdist ({package})" for package in PACKAGES),
        home=CI,
    ),
    _after_fix("Vulture dead code", "uv run --extra dev task dead", "static"),
    _after_fix("Maxitor samples: action_machine public API", "uv run --extra dev task samples-public-api", "static"),
    *(
        Step(
            f"Pytest {package}",
            f"uv run --extra dev pytest packages/{package}/tests/ -v",
            "tests",
            after=(AUTO_FIX,),
            ci_command=f'uv run --extra dev pytest packages/{package}/tests/ -v -m "not benchmark"',
        )
        for package in (
            "aoa-demo",
            "aoa-otel",
            "aoa-langgraph",
            "aoa-ocel",
            "aoa-fastapi-adapter",
            "aoa-mcp-adapter",
            "aoa-action-machine",
        )
    ),
    Step(
        "Examples: scripts, notebooks, pages, links",
        "uv run --extra dev pytest tests/examples -n auto -q",
        "examples",
        after=(AUTO_FIX,),
    ),
    Step(
        "Pytest tests/scripts (check run, graph files)",
        "uv run --extra dev pytest tests/scripts -v",
        "tests",
        after=(AUTO_FIX,),
        ci_command='uv run --extra dev pytest tests/scripts -v -m "not benchmark"',
    ),
    _after_fix("Radon cyclomatic complexity", "uv run --extra dev task cc", "static"),
    _after_fix("Radon maintainability index", "uv run --extra dev task mi", "static"),
    # Only on a green run: build this repository's graphs and update their files
    # (graph-builder.toml). Like the auto-fix, it may change files and the run stays green; the
    # changed files go into the same commit as the change that changed the graph.
    Step(
        GRAPH_WRITE,
        f"{GRAPH_BUILDER} write",
        "graphs",
        only_if_all_passed=True,
        home=LOCAL,
    ),
    # Always run, and after the write: a failure elsewhere must never leave the graph files neither
    # written nor checked, and a stale file must be rewritten by the write, not fail the run before it.
    Step(
        "Graph files (graph-builder check)",
        f"{GRAPH_BUILDER} check",
        "graphs",
        after=(AUTO_FIX, GRAPH_WRITE),
        home=BOTH,
    ),
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
    skipped: str = ""

    @property
    def ok(self) -> bool:
        """Whether the step ran and passed."""
        return self.exit_code == 0 and not self.skipped

    @property
    def failed(self) -> bool:
        """Whether the step ran and failed; a skipped step did neither."""
        return self.exit_code != 0

    def line(self, name: str) -> str:
        """The step's ``OK``/``FAIL`` line, with its exit code and duration, or why it was skipped."""
        if self.skipped:
            return f"SKIPPED {name}: {self.skipped}"
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


def _ready(step: Step, ended: set[str], running: list[_Running], steps: tuple[Step, ...]) -> bool:
    """Whether ``step`` may start now: what it waits for has ended, and nothing it must not overlap is running."""
    if step.only_if_all_passed:
        others = {other.name for other in steps if other is not step and step.name not in other.after}
        return not running and others <= ended
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


def _skip(step: Step, output: Path, failed: int) -> Result:
    """Record a last step that does not run because ``failed`` steps failed."""
    output.write_bytes(b"")
    result = Result(exit_code=0, seconds=0.0, output=output, skipped=f"{failed} step(s) failed")
    _say(YELLOW, result.line(step.name))
    return result


def _run_all(folder: Path, jobs: int, results: dict[str, Result], steps: tuple[Step, ...] = STEPS) -> None:
    """Run every step under the limit, recording in ``results`` each step as it ends."""
    pending = list(steps)
    running: list[_Running] = []
    try:
        while pending or running:
            for step in list(pending):
                if len(running) >= jobs:
                    break
                if _ready(step, set(results), running, steps):
                    pending.remove(step)
                    output = folder / f"{steps.index(step):02d}.out"
                    failed = sum(result.failed for result in results.values())
                    if step.only_if_all_passed and failed:
                        results[step.name] = _skip(step, output, failed)
                        continue
                    running.append(_start(step, output))
            for item in list(running):
                exit_code = item.process.poll()
                if exit_code is None:
                    continue
                running.remove(item)
                result = Result(exit_code=exit_code, seconds=time.monotonic() - item.started, output=item.output)
                results[item.step.name] = result
                _say(RED if result.failed else GREEN, result.line(item.step.name))
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


def _as_in_ci(step: Step) -> Step:
    """The step as CI runs it."""
    return replace(step, command=step.ci_command) if step.ci_command else step


def _select(
    steps: tuple[Step, ...],
    where: str,
    only_group: str | None,
    skip_group: str | tuple[str, ...] | None,
) -> tuple[Step, ...]:
    """The rows a selector keeps; references to rows that did not survive are dropped."""
    skipped = (skip_group,) if isinstance(skip_group, str) else tuple(skip_group or ())
    rows = list(steps)
    if only_group is not None:
        rows = [step for step in rows if step.group == only_group]
    else:
        if where != BOTH:
            rows = [step for step in rows if step.home in (where, BOTH)]
    if skipped:
        rows = [step for step in rows if step.group not in skipped]
    if where == CI:
        rows = [_as_in_ci(step) for step in rows]
    names = {step.name for step in rows}
    return tuple(
        replace(
            step,
            after=tuple(after for after in step.after if after in names),
            not_during=tuple(name for name in step.not_during if name in names),
        )
        for step in rows
    )


def _parser() -> argparse.ArgumentParser:
    """The command line: a where and the narrow selectors."""
    parser = argparse.ArgumentParser(prog="run_checks_with_log.sh", description="Run the repository's check run.")
    parser.add_argument("--where", choices=(LOCAL, CI, BOTH), default=LOCAL, help="which rows to run")
    parser.add_argument("--only-group", metavar="NAME", help="only the rows of one group")
    parser.add_argument("--skip-group", metavar="NAME", action="append", help="drop the rows of a group; may be given more than once")
    return parser


def _write_log(header: str, results: dict[str, Result], wall: float, interrupted: bool, steps: tuple[Step, ...]) -> None:
    """Join the blocks of the steps that ended, in table order, between the header and the footer."""
    with LOG_FILE.open("wb") as log:
        log.write(header.encode())
        for step in steps:
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


def main(argv: list[str] | None = None) -> int:
    """Run every selected step under the limit and return the run's exit code."""
    options = _parser().parse_args(argv)
    where = options.where
    steps = _select(STEPS, where, options.only_group, options.skip_group)
    if not steps:
        _say(RED, "FAIL no step matches the selectors")
        return 2
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
    steps_word = "step" if jobs == 1 else "steps"
    _say(YELLOW, f"Full check run (cwd={REPO_ROOT}, up to {jobs} {steps_word} at once)...")
    print()
    started = time.monotonic()
    interrupted = False
    results: dict[str, Result] = {}
    with tempfile.TemporaryDirectory(prefix="check-run-") as name:
        try:
            _run_all(Path(name), jobs, results, steps)
        except KeyboardInterrupt:
            interrupted = True
        wall = time.monotonic() - started
        _write_log(header, results, wall, interrupted, steps)
    print()
    _say(YELLOW, f"Wall time: {wall:.1f} s")
    _say(GREEN, f"Log: {LOG_FILE}")
    if interrupted:
        _say(RED, "Run interrupted")
        return 130
    failed = any(result.failed for result in results.values())
    return 1 if failed else 0


if __name__ == "__main__":
    os.chdir(REPO_ROOT)
    sys.exit(main())
