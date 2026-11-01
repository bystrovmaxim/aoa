# tests/scripts/test_check_run.py
"""The check run's last step, its selectors and its sign-off: each context sees its own rows, and only a proved commit is reported."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
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
    names = _names(runner._select(runner.STEPS, "local", False, False, None, None))
    assert not any(name.startswith("Build wheel/sdist") for name in names)
    assert "Packaging wheel install smoke" not in names


def test_ci_checks_drops_browser_and_packaging() -> None:
    """The checks job keeps the graph check and drops the browser and the packaging rows."""
    runner = _runner()
    names = _names(runner._select(runner.STEPS, "ci", False, False, None, "packaging"))
    assert "Maxitor client: the same layout in three engines" not in names
    assert not any(name.startswith("Build wheel/sdist") for name in names)
    assert "Graph files (graph-builder check)" in names


def test_fast_keeps_only_the_cheap_rows() -> None:
    """The fast mode runs the guards, the static rows and the tests, and nothing heavy."""
    runner = _runner()
    names = _names(runner._select(runner.STEPS, "local", True, False, None, None))
    assert "Ruff auto-fix" in names
    assert "Pytest aoa-ocel" in names
    assert "Maxitor client: npm ci and Vite build" not in names
    assert "Graph files (graph-builder write)" not in names


def test_fast_drops_the_speed_tests_and_the_full_run_keeps_them() -> None:
    """The fast mode is deterministic, so its Python suites leave the speed tests out; the default run keeps them."""
    runner = _runner()
    fast = runner._select(runner.STEPS, "local", True, False, None, None)
    full = runner._select(runner.STEPS, "local", False, False, None, None)
    assert all('-m "not benchmark"' in step.command for step in fast if "pytest" in step.command)
    assert not any("not benchmark" in step.command for step in full)


def test_the_browsers_run_only_locally() -> None:
    """A CI machine has no graphics card, so no CI selection holds a browser row; the local run holds it, with no system libraries asked for."""
    runner = _runner()
    assert not any(step.browser for step in runner._select(runner.STEPS, "ci", False, False, None, None))
    browsers = [step for step in runner._select(runner.STEPS, "local", False, False, None, None) if step.browser]
    assert len(browsers) == 1
    assert "--with-deps" not in browsers[0].command


def test_only_browser_includes_the_client_build_it_needs() -> None:
    """The browser selector carries the client build, which the layout check reads."""
    runner = _runner()
    names = _names(runner._select(runner.STEPS, "ci", False, True, None, None))
    assert "Maxitor client: npm ci and Vite build" in names
    assert "Maxitor client: the same layout in three engines" in names


def test_only_group_packaging_keeps_build_and_smoke() -> None:
    """The packaging selector keeps the eight builds and the install smoke."""
    runner = _runner()
    names = _names(runner._select(runner.STEPS, "ci", False, False, "packaging", None))
    assert sum(name.startswith("Build wheel/sdist") for name in names) == 8
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
    rows = runner._select(runner.STEPS, "ci", False, False, None, "packaging")
    assert next(step for step in rows if step.name == "Graph files (graph-builder check)").after == ()


def test_maxitors_build_waits_out_the_client_build() -> None:
    """Maxitor's sdist packs the client folder, so the two never overlap when one selection holds both."""
    runner = _runner()
    rows = runner._select(runner.STEPS, "ci", False, False, None, None)
    build = next(step for step in rows if step.name == "Build wheel/sdist (packages/maxitor)")
    assert build.not_during == ("Maxitor client: npm ci and Vite build",)


def _git_repo(tmp_path: Path, runner: ModuleType, monkeypatch: pytest.MonkeyPatch) -> str:
    """A repository of one commit standing in for this one, and the commit."""
    for arguments in (["init", "-q"], ["config", "user.email", "t@t"], ["config", "user.name", "t"]):
        subprocess.run(["git", *arguments], cwd=tmp_path, check=True)
    (tmp_path / "file").write_text("one\n", encoding="utf-8")
    subprocess.run(["git", "add", "file"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "one"], cwd=tmp_path, check=True)
    monkeypatch.setattr(runner, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(runner, "RECEIPT_FILE", tmp_path / ".git" / "receipt.json")
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=tmp_path, check=True, capture_output=True, text=True
    ).stdout.strip()


def test_a_green_run_on_one_commit_leaves_a_receipt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The commit the tree was, from start to end, is what the receipt names."""
    runner = _runner()
    commit = _git_repo(tmp_path, runner, monkeypatch)
    runner._leave_receipt(commit, 35)
    assert json.loads(runner.RECEIPT_FILE.read_text(encoding="utf-8")) == {"commit": commit, "steps": 35}


@pytest.mark.parametrize("case", ["dirty from the start", "dirtied during the run", "another commit by the end"])
def test_no_receipt_when_the_tree_was_not_one_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    """What ran was not the commit, so nothing is recorded: an auto-fix, a graph write or a new commit each change what was proved."""
    runner = _runner()
    commit = _git_repo(tmp_path, runner, monkeypatch)
    started_on = None if case == "dirty from the start" else commit
    if case != "another commit by the end":
        (tmp_path / "file").write_text("two\n", encoding="utf-8")
    else:
        subprocess.run(["git", "commit", "-qm", "two", "--allow-empty"], cwd=tmp_path, check=True)
    runner._leave_receipt(started_on, 35)
    assert not runner.RECEIPT_FILE.exists()


def _signed(runner: ModuleType, monkeypatch: pytest.MonkeyPatch, returncode: int = 0) -> list[list[str]]:
    """Stand in for ``gh`` and return where each call it got goes; no status leaves the test."""
    calls: list[list[str]] = []
    real_run = subprocess.run

    def run(command: list[str], **options: object) -> object:
        if command[0] != "gh":
            return real_run(command, **options)
        calls.append(command)
        return subprocess.CompletedProcess(command, returncode, "", "HTTP 422: No commit found for SHA")

    monkeypatch.setattr(runner.subprocess, "run", run)
    return calls


def test_sign_off_reports_the_proved_commit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The status goes on the commit the receipt names, under the name the merge rule requires."""
    runner = _runner()
    commit = _git_repo(tmp_path, runner, monkeypatch)
    runner._leave_receipt(commit, 35)
    calls = _signed(runner, monkeypatch)
    assert runner.main(["--sign-off"]) == 0
    assert len(calls) == 1
    assert f"repos/{{owner}}/{{repo}}/statuses/{commit}" in calls[0]
    assert "state=success" in calls[0]
    assert "context=Local check run" in calls[0]


def test_sign_off_refuses_a_tree_with_uncommitted_changes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A receipt says nothing about changes made after it."""
    runner = _runner()
    commit = _git_repo(tmp_path, runner, monkeypatch)
    runner._leave_receipt(commit, 35)
    (tmp_path / "file").write_text("two\n", encoding="utf-8")
    calls = _signed(runner, monkeypatch)
    assert runner.main(["--sign-off"]) == 1
    assert calls == []


def test_sign_off_refuses_a_commit_the_run_did_not_prove(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A new commit has no proof of its own until it is run."""
    runner = _runner()
    commit = _git_repo(tmp_path, runner, monkeypatch)
    runner._leave_receipt(commit, 35)
    subprocess.run(["git", "commit", "-qm", "two", "--allow-empty"], cwd=tmp_path, check=True)
    calls = _signed(runner, monkeypatch)
    assert runner.main(["--sign-off"]) == 1
    assert calls == []
    assert "no green browser run on record" in capsys.readouterr().out


def test_sign_off_refuses_with_no_receipt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """No full green run, nothing to report."""
    runner = _runner()
    _git_repo(tmp_path, runner, monkeypatch)
    calls = _signed(runner, monkeypatch)
    assert runner.main(["--sign-off"]) == 1
    assert calls == []


def test_sign_off_fails_when_github_takes_no_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """An unpushed commit is refused by GitHub, and the run says so instead of claiming the mark."""
    runner = _runner()
    commit = _git_repo(tmp_path, runner, monkeypatch)
    runner._leave_receipt(commit, 35)
    _signed(runner, monkeypatch, returncode=1)
    assert runner.main(["--sign-off"]) == 1
    assert "is the commit pushed?" in capsys.readouterr().out


def test_only_the_whole_local_run_touches_the_receipt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A narrow run proves less than the whole, so it neither leaves a receipt nor drops the one there is."""
    runner = _runner()
    commit = _git_repo(tmp_path, runner, monkeypatch)
    runner._leave_receipt(commit, 35)
    before = runner.RECEIPT_FILE.read_text(encoding="utf-8")
    monkeypatch.setattr(runner, "LOG_FILE", tmp_path / ".git" / "log.txt")
    monkeypatch.setattr(runner, "STEPS", (runner.Step("only", "true", "narrow"), runner.Step("other", "true", "wide")))
    assert runner.main(["--only-group", "narrow"]) == 0
    assert runner.RECEIPT_FILE.read_text(encoding="utf-8") == before
    assert runner.main([]) == 0
    assert json.loads(runner.RECEIPT_FILE.read_text(encoding="utf-8")) == {"commit": commit, "steps": 2}


def test_a_green_browser_run_alone_proves_the_commit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """CI runs everything else, so the browsers are all a pull request has to run locally."""
    runner = _runner()
    commit = _git_repo(tmp_path, runner, monkeypatch)
    monkeypatch.setattr(runner, "LOG_FILE", tmp_path / ".git" / "log.txt")
    browser = runner.Step("engines", "true", "client", browser=True, home=runner.LOCAL)
    monkeypatch.setattr(runner, "STEPS", (browser, runner.Step("other", "false", "wide")))
    assert runner.main(["--only-browser"]) == 0
    assert json.loads(runner.RECEIPT_FILE.read_text(encoding="utf-8")) == {"commit": commit, "steps": 1}


def test_a_red_whole_run_drops_the_receipt_of_the_same_commit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The latest whole run speaks for the commit: a red one takes back what an earlier green one said."""
    runner = _runner()
    commit = _git_repo(tmp_path, runner, monkeypatch)
    runner._leave_receipt(commit, 35)
    monkeypatch.setattr(runner, "LOG_FILE", tmp_path / ".git" / "log.txt")
    monkeypatch.setattr(runner, "STEPS", (runner.Step("bad", "false", "a"),))
    assert runner.main([]) == 1
    assert not runner.RECEIPT_FILE.exists()


def _github_says(runner: ModuleType, monkeypatch: pytest.MonkeyPatch, answers: list[str]) -> list[list[str]]:
    """Stand in for ``gh``: each question gets the next answer, the last one for good; the wait takes no time."""
    calls: list[list[str]] = []

    def run(command: list[str], **options: object) -> object:
        del options
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, answers[min(len(calls), len(answers)) - 1], "")

    monkeypatch.setattr(runner.subprocess, "run", run)
    monkeypatch.setattr(runner.time, "sleep", lambda seconds: None)
    return calls


def test_ci_passes_a_commit_that_carries_the_proof(monkeypatch: pytest.MonkeyPatch) -> None:
    """A commit that had its run answers at once, and CI asks about that commit and that status."""
    runner = _runner()
    calls = _github_says(runner, monkeypatch, ["success\n"])
    assert runner.main(["--await-sign-off", "abc123"]) == 0
    assert len(calls) == 1
    assert "repos/{owner}/{repo}/commits/abc123/status" in calls[0]
    assert any('select(.context == "Local check run")' in part for part in calls[0])


def test_ci_waits_for_a_run_still_going(monkeypatch: pytest.MonkeyPatch) -> None:
    """A commit pushed to an open pull request gets time for its run."""
    runner = _runner()
    calls = _github_says(runner, monkeypatch, ["", "", "success\n"])
    assert runner.main(["--await-sign-off", "abc123"]) == 0
    assert len(calls) == 3


@pytest.mark.parametrize("answer", ["", "pending\n", "failure\n"], ids=["no status", "pending", "failure"])
def test_ci_fails_a_commit_with_no_proof(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], answer: str
) -> None:
    """Only a success is a proof, and the failure says what to do."""
    runner = _runner()
    _github_says(runner, monkeypatch, [answer])
    monkeypatch.setattr(runner, "SIGN_OFF_WAIT_SECONDS", 0)
    assert runner.main(["--await-sign-off", "abc123"]) == 1
    assert "bash scripts/check_before_pr.sh" in capsys.readouterr().out


def test_ci_reads_the_proof_of_the_pull_requests_own_commit() -> None:
    """``github.sha`` is GitHub's merge commit, which nobody ran, so the proof could never be there."""
    workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "COMMIT: ${{ github.event.pull_request.head.sha }}" in workflow
    assert 'check_run.py --await-sign-off "$COMMIT"' in workflow


def _pr_repo(tmp_path: Path) -> tuple[Path, Path]:
    """A repository pushed to a bare one, with the real two scripts and a run that records how it was called."""
    origin, work = tmp_path / "origin.git", tmp_path / "work"
    subprocess.run(["git", "init", "-q", "--bare", str(origin)], check=True)
    subprocess.run(["git", "clone", "-q", str(origin), str(work)], check=True, capture_output=True)
    for arguments in (
        ["config", "user.email", "t@t"],
        ["config", "user.name", "t"],
        ["commit", "-qm", "one", "--allow-empty"],
        ["push", "-q", "origin", "HEAD"],
    ):
        subprocess.run(["git", *arguments], cwd=work, check=True)
    calls = tmp_path / "calls"
    scripts = work / "scripts"
    scripts.mkdir()
    (work / ".gitignore").write_text("scripts/\n", encoding="utf-8")
    for name in ("check_before_commit.sh", "check_before_pr.sh"):
        shutil.copy(REPO_ROOT / "scripts" / name, scripts / name)
    (scripts / "run_checks_with_log.sh").write_text(f'echo "$*" >> {calls}\nexit ${{RUN_EXIT:-0}}\n', encoding="utf-8")
    subprocess.run(["git", "add", ".gitignore"], cwd=work, check=True)
    subprocess.run(["git", "commit", "-qm", "ignore"], cwd=work, check=True)
    subprocess.run(["git", "push", "-q", "origin", "HEAD"], cwd=work, check=True)
    return work, calls


def _calls(calls: Path) -> list[str]:
    """How the run was called, one entry per call; an empty string is the full run."""
    return calls.read_text(encoding="utf-8").splitlines() if calls.exists() else []


def test_before_commit_is_the_fast_run(tmp_path: Path) -> None:
    """During the work and before a commit: the cheap steps, with what the caller adds passed on."""
    work, calls = _pr_repo(tmp_path)
    subprocess.run(["bash", "scripts/check_before_commit.sh", "--skip-group", "tests"], cwd=work, check=True)
    assert _calls(calls) == ["--fast --skip-group tests"]


def test_before_pr_runs_the_browsers_then_signs_off(tmp_path: Path) -> None:
    """On a pushed commit: only what CI cannot run, and then its proof."""
    work, calls = _pr_repo(tmp_path)
    subprocess.run(["bash", "scripts/check_before_pr.sh"], cwd=work, check=True)
    assert _calls(calls) == ["--only-browser", "--sign-off"]


def test_before_pr_signs_nothing_after_a_red_run(tmp_path: Path) -> None:
    """A red run is reported with its own code, and no proof leaves."""
    work, calls = _pr_repo(tmp_path)
    run = subprocess.run(
        ["bash", "scripts/check_before_pr.sh"], cwd=work, check=False, env={**os.environ, "RUN_EXIT": "1"}
    )
    assert run.returncode == 1
    assert _calls(calls) == ["--only-browser"]


def test_before_pr_refuses_uncommitted_changes_before_the_run(tmp_path: Path) -> None:
    """The run would prove nothing, so it is not spent."""
    work, calls = _pr_repo(tmp_path)
    (work / "new").write_text("x\n", encoding="utf-8")
    run = subprocess.run(["bash", "scripts/check_before_pr.sh"], cwd=work, check=False, capture_output=True, text=True)
    assert (run.returncode, _calls(calls)) == (1, [])
    assert "uncommitted changes" in run.stdout


def test_before_pr_refuses_an_unpushed_commit_before_the_run(tmp_path: Path) -> None:
    """GitHub could not take the status, so the run is not spent."""
    work, calls = _pr_repo(tmp_path)
    subprocess.run(["git", "commit", "-qm", "two", "--allow-empty"], cwd=work, check=True)
    run = subprocess.run(["bash", "scripts/check_before_pr.sh"], cwd=work, check=False, capture_output=True, text=True)
    assert (run.returncode, _calls(calls)) == (1, [])
    assert "not pushed" in run.stdout
