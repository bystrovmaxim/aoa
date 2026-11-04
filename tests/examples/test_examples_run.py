# tests/examples/test_examples_run.py
"""
Smoke test: every ``examples/**/*.py`` tutorial script runs to completion.

Chapter 3.5 implementation audit, finding 6: a breaking change to a core mechanism
(``reason=`` mandatory on ``grant()``/``check_roles()``, ``AccessVerdict`` collapsing
``allowed``/``level`` to ``kind``/``reason``) updated every reader inside ``packages/``
and its tests, but silently missed three scripts under ``examples/`` — a directory no
other automated check ever touches. The breakage was invisible to CI and only surfaced
when a human ran the tutorial by hand.

This test is the "at least import them" guard the audit's own finding suggested, made
slightly stronger: every script is actually *run* (``uv run python examples/.../NN_x.py``,
exactly as a tutorial reader would), not merely imported — most of these scripts have no
``if __name__ == "__main__":`` guard, so importing one already runs it in full, and a
plain import would miss anything gated behind ``asyncio.run(main())`` if that pattern
ever changes.

Each script is its own parametrized test node: one failure never hides another, and the
failure message carries the script's stdout/stderr for a same-glance diagnosis.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_ROOT = REPO_ROOT / "examples"
_TIMEOUT_SECONDS = 60


def _is_in_package(script: Path) -> bool:
    """Whether ``script`` is a module of a package folder an example imports, not an example."""
    return any((parent / "__init__.py").exists() for parent in script.parents if parent != EXAMPLES_ROOT and EXAMPLES_ROOT in parent.parents)


def _discover_example_scripts() -> list[Path]:
    return sorted(p for p in EXAMPLES_ROOT.rglob("*.py") if "__pycache__" not in p.parts and not _is_in_package(p))


def _example_id(script: Path) -> str:
    return script.relative_to(EXAMPLES_ROOT).as_posix()


_SCRIPTS = _discover_example_scripts()


@pytest.mark.parametrize("script", _SCRIPTS, ids=_example_id)
def test_example_script_runs_without_error(script: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=_TIMEOUT_SECONDS,
    )
    assert result.returncode == 0, (
        f"{_example_id(script)} exited {result.returncode}\n"
        f"--- stdout ---\n{result.stdout}\n"
        f"--- stderr ---\n{result.stderr}"
    )
