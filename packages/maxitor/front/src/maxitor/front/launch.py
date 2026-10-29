# packages/maxitor/front/src/maxitor/front/launch.py
"""
Start a part of Maxitor from its command, or name the extra it needs.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Every part's code is in the ``maxitor`` wheel, but only an extra brings a part's
dependencies. A command whose extra is missing says which one to install
instead of failing on an import.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

The command ``maxitor`` → ``main()`` → imports the front's server inside the
function → runs it. A ``ModuleNotFoundError`` for a dependency the extra brings
becomes one line on standard error and exit code 2; any other error propagates.
Nothing heavy is imported at module level, so this module loads without any extra.
"""

from __future__ import annotations

import importlib
import sys

FRONT_HINT = 'maxitor needs its front: pip install "maxitor[front]"'


def _brought_by_front(error: ModuleNotFoundError) -> bool:
    """Whether the missing module is one the ``front`` extra installs."""
    brought = {"aoa", "fastapi", "starlette", "uvicorn", "duckdb", "httpx", "websockets"}
    return (error.name or "").split(".")[0] in brought


def main() -> None:
    """
    AI-CORE-BEGIN
    ROLE: Entry point of the ``maxitor`` command: run Maxitor's server.
    CONTRACT: Without the ``front`` extra, writes ``FRONT_HINT`` to standard error and exits 2; any other error propagates.
    AI-CORE-END
    """
    try:
        server = importlib.import_module("maxitor.front.api.main")
    except ModuleNotFoundError as error:
        if not _brought_by_front(error):
            raise
        sys.stderr.write(FRONT_HINT + "\n")
        raise SystemExit(2) from None
    server.run()
