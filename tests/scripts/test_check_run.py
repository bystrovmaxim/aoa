# tests/scripts/test_check_run.py
"""The check run's last step: it runs after every other step, and only when all of them passed."""

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
