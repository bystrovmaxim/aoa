# tests/scripts/test_check_run.py
"""The check run's last step and its selectors: each context sees its own rows."""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import replace
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
    names = _names(runner._select(runner.STEPS, "local", None, None))
    assert not any(name.startswith("Build wheel/sdist") for name in names)
    assert "Packaging wheel install smoke" not in names


def test_ci_checks_drops_the_packaging() -> None:
    """The checks job keeps the graph check and drops the packaging rows."""
    runner = _runner()
    names = _names(runner._select(runner.STEPS, "ci", None, "packaging"))
    assert not any(name.startswith("Build wheel/sdist") for name in names)
    assert "Graph files (graph-builder check)" in names


EXAMPLES = "Examples: scripts, notebooks, pages, links"


def test_the_examples_run_in_a_local_run() -> None:
    """A local run checks every example with everything else."""
    runner = _runner()
    rows = {step.name: step for step in runner._select(runner.STEPS, "local", None, None)}
    assert "pytest tests/examples -n auto" in rows[EXAMPLES].command


def test_the_examples_job_runs_the_examples_alone() -> None:
    """CI's Examples job runs that one step, on a machine of its own."""
    runner = _runner()
    assert [step.name for step in runner._select(runner.STEPS, "ci", "examples", None)] == [EXAMPLES]


def test_the_checks_jobs_leave_the_examples_to_their_job() -> None:
    """CI's Checks jobs drop both the packaging and the examples, and keep the rest."""
    runner = _runner()
    names = _names(runner._select(runner.STEPS, "ci", None, ("packaging", "examples")))
    assert EXAMPLES not in names
    assert not any(name.startswith("Build wheel/sdist") for name in names)
    assert "Graph files (graph-builder check)" in names


def test_skip_group_may_be_given_more_than_once() -> None:
    """The command line collects every --skip-group it is given."""
    options = _runner()._parser().parse_args(["--skip-group", "packaging", "--skip-group", "examples"])
    assert options.skip_group == ["packaging", "examples"]


def test_the_fast_mode_is_refused() -> None:
    """The closing run is CI's, so no cheaper local run exists."""
    runner = _runner()
    with pytest.raises(SystemExit):
        runner._parser().parse_args(["--fast"])


def test_the_full_run_keeps_the_speed_tests() -> None:
    """Only CI leaves the speed tests out."""
    runner = _runner()
    full = runner._select(runner.STEPS, "local", None, None)
    assert not any("not benchmark" in step.command for step in full)


def _ruff_rows(rows: tuple) -> list:
    """The rows of a selection that run Ruff."""
    return [step for step in rows if "ruff" in step.command or "task lint" in step.command]


def test_one_ruff_row_in_every_selection() -> None:
    """Fixing and linting are one step locally and in CI."""
    runner = _runner()
    for where in ("local", "ci"):
        assert [step.name for step in _ruff_rows(runner._select(runner.STEPS, where, None, None))] == [
            "Ruff auto-fix"
        ]


def test_ruff_fixes_locally() -> None:
    """The full run on a machine fixes what it can."""
    runner = _runner()
    assert "--fix" in _ruff_rows(runner._select(runner.STEPS, "local", None, None))[0].command


def test_ruff_in_ci_reports_and_never_changes_the_tree() -> None:
    """CI must not rewrite files, and this is the only Ruff check a pull request gets."""
    runner = _runner()
    command = _ruff_rows(runner._select(runner.STEPS, "ci", None, None))[0].command
    assert "ruff check" in command
    assert "--fix" not in command
    assert "packages/ tests/ scripts/" in command


def test_only_group_packaging_keeps_build_and_smoke() -> None:
    """The packaging selector keeps the seven builds and the install smoke."""
    runner = _runner()
    names = _names(runner._select(runner.STEPS, "ci", "packaging", None))
    assert sum(name.startswith("Build wheel/sdist") for name in names) == 7
    assert "Packaging wheel install smoke" in names


def _graph_rows(runner, graph_file: Path) -> tuple:
    """The table's own two graph rows, with commands that write and read ``graph_file``: only their order is under test."""
    check, write = "Graph files (graph-builder check)", "Graph files (graph-builder write)"
    rows = {step.name: step for step in runner.STEPS}
    return (
        replace(rows[write], command=f"echo current > {graph_file}"),
        replace(
            rows[check],
            command=f"grep -q current {graph_file}",
            after=tuple(a for a in rows[check].after if a == write),
        ),
    )


def test_a_stale_graph_file_is_rewritten_on_a_green_run(tmp_path: Path) -> None:
    """The write comes before the check, so a stale file is rewritten and the run stays green."""
    runner = _runner()
    graph_file = tmp_path / "graph.json"
    graph_file.write_text("stale\n", encoding="utf-8")
    results: dict = {}
    runner._run_all(tmp_path, 4, results, (runner.Step("good", "true", "a"), *_graph_rows(runner, graph_file)))
    assert all(result.ok for result in results.values()), {name: result.line(name) for name, result in results.items()}
    assert graph_file.read_text(encoding="utf-8") == "current\n"


def test_the_graph_check_runs_even_after_a_failure(tmp_path: Path) -> None:
    """A failure elsewhere skips the write, and the check still runs and reports the stale file."""
    runner = _runner()
    graph_file = tmp_path / "graph.json"
    graph_file.write_text("stale\n", encoding="utf-8")
    results: dict = {}
    runner._run_all(tmp_path, 4, results, (runner.Step("bad", "false", "a"), *_graph_rows(runner, graph_file)))
    assert results["Graph files (graph-builder write)"].skipped
    assert results["Graph files (graph-builder check)"].failed
    assert graph_file.read_text(encoding="utf-8") == "stale\n"


def test_the_graph_check_has_no_write_to_wait_for_in_ci() -> None:
    """CI selects no write, so the check does not wait for one."""
    runner = _runner()
    rows = runner._select(runner.STEPS, "ci", None, "packaging")
    assert next(step for step in rows if step.name == "Graph files (graph-builder check)").after == (runner.AUTO_FIX,)


def test_text_only_changes_skip_every_gate_job_but_versions() -> None:
    """Each heavy job names the ``changes`` job, so a text-only pull request does not run it."""
    workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert workflow.count("needs.changes.outputs.code == 'true'") == 5
