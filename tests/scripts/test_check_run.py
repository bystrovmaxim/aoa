# tests/scripts/test_check_run.py
"""The check run's last step and its selectors: the last step runs only on a green run, and each context sees its own rows."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _runner() -> ModuleType:
    """``scripts/check_run.py`` as a module; it is a script, not a package."""
    spec = importlib.util.spec_from_file_location("check_run", REPO_ROOT / "scripts" / "check_run.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_run"] = module
    spec.loader.exec_module(module)
    return module


def _run(tmp_path: Path, first: str) -> tuple[ModuleType, dict, Path]:
    """Run two steps — ``first`` and a slower ``true`` — then a last step that leaves a mark when it runs."""
    runner = _runner()
    mark = tmp_path / "ran"
    steps = (
        runner.Step("first", first, "a"),
        runner.Step("slow", "sleep 0.3", "a"),
        runner.Step("last", f"touch {mark}", "b", only_if_all_passed=True),
    )
    results: dict = {}
    runner._run_all(tmp_path, 4, results, steps)
    return runner, results, mark


def test_the_last_step_runs_after_a_green_run(tmp_path: Path) -> None:
    """Every other step passed: the last step runs, and it ran after the slowest of them."""
    _, results, mark = _run(tmp_path, "true")
    assert mark.exists()
    assert results["last"].ok and not results["last"].skipped
    assert list(results) == ["first", "slow", "last"]


def test_the_last_step_is_skipped_after_a_failure(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A step failed: the last step does not run, and it is neither OK nor FAIL."""
    _, results, mark = _run(tmp_path, "false")
    assert not mark.exists()
    last = results["last"]
    assert (last.ok, last.failed, last.line("last")) == (False, False, "SKIPPED last: 1 step(s) failed")
    assert "SKIPPED last: 1 step(s) failed" in capsys.readouterr().out


def _names(steps: tuple) -> set[str]:
    """The names of a selected set of steps."""
    return {step.name for step in steps}


def test_local_run_drops_the_packaging_steps() -> None:
    """The local full run selects no build and no install smoke; the network steps are CI only."""
    runner = _runner()
    names = _names(runner._select(runner.STEPS, "local", False, False, False, None, None))
    assert not any(name.startswith("Build wheel/sdist") for name in names)
    assert "Packaging wheel install smoke" not in names


def test_ci_checks_drops_browser_and_packaging() -> None:
    """The checks job keeps the graph check and drops the browser and the packaging rows."""
    runner = _runner()
    names = _names(runner._select(runner.STEPS, "ci", False, False, True, None, "packaging"))
    assert "Maxitor client: the same layout in three engines" not in names
    assert not any(name.startswith("Build wheel/sdist") for name in names)
    assert "Graph files (graph-builder check)" in names


def test_fast_keeps_only_the_cheap_rows() -> None:
    """The fast mode runs the guards, the static rows and the tests, and nothing heavy."""
    runner = _runner()
    names = _names(runner._select(runner.STEPS, "local", True, False, False, None, None))
    assert "Ruff auto-fix" in names
    assert "Pytest aoa-ocel" in names
    assert "Maxitor client: npm ci and Vite build" not in names
    assert "Benchmark and timing tests" not in names
    assert "Graph files (graph-builder write)" not in names


def test_only_browser_includes_the_client_build_it_needs() -> None:
    """The browser selector carries the client build, which the layout check reads."""
    runner = _runner()
    names = _names(runner._select(runner.STEPS, "ci", False, True, False, None, None))
    assert "Maxitor client: npm ci and Vite build" in names
    assert "Maxitor client: the same layout in three engines" in names


def test_only_group_packaging_keeps_build_and_smoke() -> None:
    """The packaging selector keeps the eight builds and the install smoke."""
    runner = _runner()
    names = _names(runner._select(runner.STEPS, "ci", False, False, False, "packaging", None))
    assert sum(name.startswith("Build wheel/sdist") for name in names) == 8
    assert "Packaging wheel install smoke" in names


def test_the_graph_check_runs_even_after_a_failure(tmp_path: Path) -> None:
    """The always-run check step survives a failing sibling; the green-only write does not."""
    runner = _runner()
    mark = tmp_path / "checked"
    steps = (
        runner.Step("bad", "false", "a"),
        runner.Step("graph-check", f"touch {mark}", "a"),
        runner.Step("graph-write", "true", "a", only_if_all_passed=True),
    )
    results: dict = {}
    runner._run_all(tmp_path, 4, results, steps)
    assert mark.exists()
    assert results["graph-check"].ok
    assert results["graph-write"].skipped
