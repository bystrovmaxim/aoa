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

# Known-broken scripts, excluded from the pass/fail gate but not silently dropped: each
# still runs and is expected to fail for a specific, tracked, unrelated reason. strict=True
# so a future fix flips this to an error instead of staying quietly green forever — whoever
# fixes issue #83 is forced to also delete the matching entry here.
_XFAIL_REASONS: dict[str, str] = {
    "extensions/02_langgraph.py": "aoa.langgraph no longer exports LangGraphAdapter (issue #83 rework, in progress)",
    "step_14_langgraph/01_external_connection.py": (
        "graph references aoa.langgraph.controller.LangGraphController, which no longer "
        "exists (issue #83 rework, in progress)"
    ),
    "step_14_langgraph/01_langgraph.py": "aoa.langgraph no longer exports LangGraphAdapter (issue #83 rework, in progress)",
    "step_14_langgraph/05_testing.py": "RouteKeyError: route key 'UNSET' not found (issue #83 rework, in progress)",
}


def _discover_example_scripts() -> list[Path]:
    return sorted(p for p in EXAMPLES_ROOT.rglob("*.py") if "__pycache__" not in p.parts)


def _example_id(script: Path) -> str:
    return str(script.relative_to(EXAMPLES_ROOT))


_SCRIPTS = _discover_example_scripts()


def _make_param(script: Path) -> pytest.param:
    rel = _example_id(script)
    reason = _XFAIL_REASONS.get(rel)
    marks = [pytest.mark.xfail(reason=reason, strict=True)] if reason else []
    return pytest.param(script, id=rel, marks=marks)


@pytest.mark.parametrize("script", [_make_param(p) for p in _SCRIPTS])
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


def test_every_xfail_entry_still_exists() -> None:
    """Catch the opposite drift: a stale xfail entry for a script that got deleted/renamed."""
    known_paths = {_example_id(p) for p in _SCRIPTS}
    stale = set(_XFAIL_REASONS) - known_paths
    assert not stale, f"xfail entries with no matching script (rename/delete happened?): {stale}"
