"""The rules of ``scripts/check_radon.py``: what fails, what is named, and when an exception stops holding."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "check_radon.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_radon", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_radon"] = module
    spec.loader.exec_module(module)
    return module


check = _load()


def _block(name: str, rank: str, complexity: int, **extra: Any) -> dict[str, Any]:
    """One block of Radon's complexity report."""
    return {"type": "function", "name": name, "rank": rank, "complexity": complexity, "lineno": 7, **extra}


def test_complexity_twenty_passes_and_twenty_one_fails() -> None:
    assert check.cc_findings({"a.py": [_block("fine", "C", 20)]}, {}) == []
    assert check.cc_findings({"a.py": [_block("heavy", "D", 21)]}, {}) == ["a.py:7 heavy — grade D (complexity 21)"]


@pytest.mark.parametrize("rank", ["D", "E", "F"])
def test_every_grade_from_d_down_fails(rank: str) -> None:
    assert len(check.cc_findings({"a.py": [_block("heavy", rank, 40)]}, {})) == 1


def test_all_offenders_are_listed() -> None:
    report = {"a.py": [_block("one", "D", 21), _block("two", "E", 31)], "b.py": [_block("three", "F", 41)]}
    assert len(check.cc_findings(report, {})) == 3


def test_a_method_reads_with_its_class() -> None:
    block = _block("run", "D", 22, type="method", classname="Worker")
    assert check.cc_findings({"a.py": [block]}, {}) == ["a.py:7 Worker.run — grade D (complexity 22)"]


def test_an_excepted_function_passes() -> None:
    assert check.cc_findings({"a.py": [_block("heavy", "D", 21)]}, {("a.py", "heavy"): "A table of cases."}) == []


def test_an_exception_for_a_function_no_longer_over_the_limit_fails() -> None:
    findings = check.cc_findings({"a.py": [_block("heavy", "C", 20)]}, {("a.py", "heavy"): "It was long."})
    assert findings == ["a.py heavy — stale exception: not over the limit any more"]


def test_an_exception_for_a_function_that_is_gone_fails() -> None:
    assert len(check.cc_findings({"a.py": []}, {("a.py", "gone"): "It was long."})) == 1


def test_an_exception_with_no_reason_fails_and_excuses_nothing() -> None:
    findings = check.cc_findings({"a.py": [_block("heavy", "D", 21)]}, {("a.py", "heavy"): "  "})
    assert findings == ["a.py:7 heavy — grade D (complexity 21)", "a.py heavy — exception has no reason"]


def test_a_file_radon_could_not_read_fails_complexity() -> None:
    assert check.cc_findings({"a.py": {"error": "invalid syntax"}}, {}) == [
        "a.py — Radon could not read it: invalid syntax"
    ]


@pytest.mark.parametrize("rank", ["B", "C"])
def test_a_module_below_a_fails(rank: str) -> None:
    assert check.mi_findings({"a.py": {"mi": 11.45, "rank": rank}}, {}) == [f"a.py — grade {rank} (index 11.45)"]


def test_a_module_at_a_passes() -> None:
    assert check.mi_findings({"a.py": {"mi": 20.0, "rank": "A"}}, {}) == []


def test_an_excepted_module_passes() -> None:
    assert check.mi_findings({"a.py": {"mi": 11.45, "rank": "B"}}, {"a.py": "Generated tables."}) == []


def test_a_stale_module_exception_fails() -> None:
    assert check.mi_findings({"a.py": {"mi": 50.0, "rank": "A"}}, {"a.py": "It was long."}) == [
        "a.py — stale exception: not over the limit any more"
    ]


def test_a_module_exception_with_no_reason_fails() -> None:
    findings = check.mi_findings({"a.py": {"mi": 11.45, "rank": "B"}}, {"a.py": "  "})
    assert findings == ["a.py — grade B (index 11.45)", "a.py — exception has no reason"]


def test_a_file_radon_could_not_read_fails_maintainability() -> None:
    assert check.mi_findings({"a.py": {"error": "invalid syntax"}}, {}) == [
        "a.py — Radon could not read it: invalid syntax"
    ]


def _radon_answers(monkeypatch: pytest.MonkeyPatch, returncode: int, stdout: str, stderr: str = "") -> None:
    """Make the Radon subprocess answer with these."""
    answer = subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)
    monkeypatch.setattr(check.subprocess, "run", lambda *_args, **_kwargs: answer)


@pytest.mark.parametrize(
    ("returncode", "stdout"),
    [(1, '{"a.py": []}'), (0, ""), (0, "not json"), (0, "{}"), (0, "[]")],
)
def test_a_report_that_cannot_be_read_fails(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], returncode: int, stdout: str
) -> None:
    _radon_answers(monkeypatch, returncode, stdout, "radon broke")
    assert check.main(["cc"]) == 1
    assert "could not be read" in capsys.readouterr().out


def test_main_passes_on_a_clean_report(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    _radon_answers(monkeypatch, 0, json.dumps({"a.py": [_block("fine", "A", 1)]}))
    assert check.main(["cc"]) == 0
    assert "over the limit: 0" in capsys.readouterr().out


def test_main_fails_and_counts_what_it_found(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _radon_answers(monkeypatch, 0, json.dumps({"a.py": {"mi": 11.45, "rank": "B"}}))
    assert check.main(["mi"]) == 1
    out = capsys.readouterr().out
    assert "a.py — grade B (index 11.45)" in out
    assert "1 finding" in out


def test_an_excepted_offender_prints_its_reason(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _radon_answers(monkeypatch, 0, json.dumps({"a.py": {"mi": 11.45, "rank": "B"}}))
    monkeypatch.setattr(check, "MODULE_EXCEPTIONS", {"a.py": "Generated tables."})
    assert check.main(["mi"]) == 0
    assert "excepted: a.py — Generated tables." in capsys.readouterr().out


def test_an_unknown_argument_is_a_usage_error() -> None:
    with pytest.raises(SystemExit) as stopped:
        check.main(["nonsense"])
    assert stopped.value.code == 2
