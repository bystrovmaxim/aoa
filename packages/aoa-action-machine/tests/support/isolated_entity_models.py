# packages/aoa-action-machine/tests/support/isolated_entity_models.py
"""
Run a declared entity model in a fresh interpreter.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The completeness rule (issue #259) enumerates **every** loaded ``@entity`` class,
including hosts marked ``exclude_graph_model``. An intentionally invalid declaration
defined at module level therefore poisons model assembly for every other test in the
same interpreter. The only clean isolation is a fresh process: the declaration is
created, judged and discarded inside a subprocess, so the parent process never sees it.

This helper runs a self-contained model source in ``sys.executable`` with the
action-machine and maxitor ``src`` roots on ``sys.path``. It is the single entry point
for subprocess-isolated entity tests.

═══════════════════════════════════════════════════════════════════════════════
SCOPE (IN / OUT)
═══════════════════════════════════════════════════════════════════════════════

**In scope**
    Running a declared-model source in a fresh process and returning its exit code,
    stdout and stderr.
    Supplying a standard ``sys.path`` preamble for ``aoa.action_machine`` /
    ``maxitor.viewer`` imports.

**Out of scope**
    Declaring entities itself; callers pass a complete source string.
    Loading ``packages/aoa-demo`` or any Russian/draft artifact — the preamble only
    ever exposes the two permitted ``src`` roots above, and no forbidden path is read.

═══════════════════════════════════════════════════════════════════════════════
RATIONALE
═══════════════════════════════════════════════════════════════════════════════

``exclude_graph_model`` must not become a validation bypass: after this feature a
graph-excluded host is still judged for declaration completeness. Defining the invalid
fixture in a subprocess keeps it a real ``@entity`` declaration (so the rules see it)
without leaving it registered in the shared interpreter.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap
from dataclasses import dataclass
from pathlib import Path

# packages/aoa-action-machine/tests/support -> repository root (parents[0..3] are the
# ``tests/support`` chain, parents[4] is the repo root).
REPO_ROOT = Path(__file__).resolve().parents[4]

# The only import roots the helper exposes. Never add a demo or draft path here.
# ``from __future__ import annotations`` is first so fixture scripts may use postponed
# annotations for cross-module forward references without circular imports.
_PRELUDE = textwrap.dedent(
    """
    from __future__ import annotations

    import sys
    sys.path.insert(0, "packages/aoa-action-machine/src")
    sys.path.insert(0, "packages/maxitor/app/src")
    """
)


@dataclass(frozen=True)
class IsolatedRunResult:
    """Outcome of one subprocess model run."""

    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        """True when the subprocess exited zero."""
        return self.returncode == 0


def run_isolated_model(source: str, *, timeout: int = 180) -> IsolatedRunResult:
    """
    Run ``source`` in a fresh interpreter and return its captured outcome.

    Args:
        source: A self-contained Python program that declares entities and judges them.
        timeout: Subprocess wall-clock limit in seconds.

    Returns:
        The exit code, stdout and stderr of the subprocess.

    The subprocess runs with the repository root as its working directory and the
    action-machine/maxitor ``src`` roots prepended to ``sys.path``. No forbidden
    package or draft path is added.
    """
    script = _PRELUDE + "\n" + textwrap.dedent(source)
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return IsolatedRunResult(result.returncode, result.stdout, result.stderr)
