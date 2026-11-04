# tests/examples/test_round_trip_runner.py
"""
The example runner reads back every Result a script builds, and fails on a difference.

Issue #409, rule 2 of #399. Each case writes a small script and runs it through
``round_trip_runner.py`` as the example test does.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

RUNNER = Path(__file__).with_name("round_trip_runner.py")

_HEADER = """
from typing import Annotated
from pydantic import Field, PlainSerializer
from aoa.action_machine.model import BaseResult
"""


def _run(tmp_path: Path, body: str) -> subprocess.CompletedProcess[str]:
    script = tmp_path / "example.py"
    script.write_text(_HEADER + body, encoding="utf-8")
    return subprocess.run([sys.executable, str(RUNNER), str(script)], capture_output=True, text=True, check=False)


def test_a_result_that_reads_back_different_fails_the_script(tmp_path: Path) -> None:
    """A Result whose JSON reads back as another value is named with the difference."""
    run = _run(
        tmp_path,
        """
class CountResult(BaseResult):
    count: Annotated[int, PlainSerializer(lambda value: value + 1, return_type=int)] = Field(description="Count")

print(CountResult(count=1).count)
""",
    )
    assert run.returncode == 1
    assert run.stdout == "1\n"
    assert "round trip: CountResult reads back different: $.count: 1 != 2" in run.stderr


def test_results_built_every_way_are_read_back(tmp_path: Path) -> None:
    """Results from the constructor, model_validate and model_validate_json are all read back."""
    run = _run(
        tmp_path,
        """
class CountResult(BaseResult):
    count: Annotated[int, PlainSerializer(lambda value: value + 1, return_type=int)] = Field(description="Count")

CountResult.model_validate({"count": 1})
CountResult.model_validate_json('{"count": 5}')
""",
    )
    assert run.returncode == 1
    assert "$.count: 1 != 2" in run.stderr
    assert "$.count: 5 != 6" in run.stderr


def test_a_script_whose_results_read_back_the_same_keeps_its_output(tmp_path: Path) -> None:
    """The runner adds nothing when every Result reads back the same."""
    run = _run(
        tmp_path,
        """
class LabelResult(BaseResult):
    label: str = Field(description="Label")

print(LabelResult(label="ok").label)
""",
    )
    assert (run.returncode, run.stdout, run.stderr) == (0, "ok\n", "")


def test_a_script_that_exits_with_an_error_keeps_its_exit_code(tmp_path: Path) -> None:
    """A failing example still fails as itself."""
    assert _run(tmp_path, "raise SystemExit(3)\n").returncode == 3


def test_the_script_folder_is_importable_as_with_python(tmp_path: Path) -> None:
    """A sibling module imports, as it does under ``python script.py``."""
    (tmp_path / "sibling.py").write_text("WORD = 'beside'\n", encoding="utf-8")
    run = _run(tmp_path, "from sibling import WORD\nprint(WORD)\n")
    assert (run.returncode, run.stdout) == (0, "beside\n")
