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

Each step also states its group, the steps it waits for and the steps it must
not overlap. This revision still runs the table in order, one step at a time.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    run_checks_with_log.sh  ──exec──►  check_run.py
                                           │
                       STEPS (table order) ▼
                 bash -c <command>  ──output──►  archive/logs/check-all.txt
                       │
                       └──► console: > name / OK|FAIL name (exit N, s)

Python's standard library only: the runner starts before anything is installed
or built, and must not depend on what it checks.
"""

from __future__ import annotations

import os
import subprocess
import sys
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


def _guard(name: str, guard: str, function: str) -> Step:
    """A shell guard, run by the entry script and logged as it always was: no blank line before its result."""
    return Step(
        name=name,
        command=f"bash scripts/run_checks_with_log.sh --guard {guard}",
        group="first",
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
    _guard("Ban __getattr__ in package __init__.py", "lazy-init-getattr", "check_no_lazy_init_getattr"),
    _guard(
        "Maxitor client: README beside components/*/ index.ts",
        "client-component-readmes",
        "check_maxitor_client_component_readmes",
    ),
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
    Step(AUTO_FIX, "uv run --extra dev ruff check --fix packages/ tests/ scripts/ aoa_run/", "first"),
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
    ROLE: What one step left behind: its exit code and how long it took.
    CONTRACT: ``exit_code`` 0 is ``OK``, anything else ``FAIL``; ``seconds`` is wall time from a monotonic clock.
    AI-CORE-END
    """

    exit_code: int
    seconds: float

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


def _write_header(log: Path) -> None:
    """Start the log with today's header."""
    now = datetime.now().astimezone()
    log.write_text(
        "==================================================\n"
        "ActionMachine project checks\n"
        f"Date: {now.strftime('%a %b %d %H:%M:%S %Z %Y')}\n"
        f"Time: {now.strftime('%H:%M:%S')}\n"
        f"Repository: {REPO_ROOT}\n"
        "==================================================\n"
        "\n",
        encoding="utf-8",
    )


def _run_step(step: Step, log: Path) -> Result:
    """Run one step from the repository root, appending its block to the log."""
    _say(YELLOW, f"> {step.name}")
    with log.open("a", encoding="utf-8") as handle:
        handle.write(f"=== {step.name} ===\n$ {step.log_command}\n\n")
    started = time.monotonic()
    with log.open("ab") as handle:
        exit_code = subprocess.run(
            ["bash", "-c", step.command],
            cwd=REPO_ROOT,
            stdout=handle,
            stderr=subprocess.STDOUT,
            check=False,
        ).returncode
    result = Result(exit_code=exit_code, seconds=time.monotonic() - started)
    _say(GREEN if result.ok else RED, result.line(step.name))
    with log.open("a", encoding="utf-8") as handle:
        gap = "\n" if step.blank_before_result else ""
        handle.write(f"{gap}{result.line(step.name)}\n\n")
    return result


def main() -> int:
    """Run every step in table order and return the run's exit code."""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    _say(YELLOW, f"Log file: {LOG_FILE}")
    print()
    _write_header(LOG_FILE)
    _say(YELLOW, f"Full check run (cwd={REPO_ROOT})...")
    print()
    started = time.monotonic()
    results = [_run_step(step, LOG_FILE) for step in STEPS]
    wall = time.monotonic() - started
    with LOG_FILE.open("a", encoding="utf-8") as handle:
        handle.write(
            "==================================================\n"
            "All steps finished (see FAIL lines above or in the log if anything failed)\n"
            f"Wall time: {wall:.1f} s\n"
            f"Log: {LOG_FILE}\n"
            "==================================================\n"
        )
    print()
    _say(YELLOW, f"Wall time: {wall:.1f} s")
    _say(GREEN, f"Log: {LOG_FILE}")
    return 0 if all(result.ok for result in results) else 1


if __name__ == "__main__":
    os.chdir(REPO_ROOT)
    sys.exit(main())
