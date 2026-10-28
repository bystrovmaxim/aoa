# packages/maxitor/src/maxitor/launch.py
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

The command ``maxitor-api`` → ``viewer()`` → imports the viewer inside the
function → runs it. A ``ModuleNotFoundError`` for a dependency the extra brings
becomes one line on standard error and exit code 2; any other error propagates.
Nothing heavy is imported at module level, so this module loads without any extra.
"""

from __future__ import annotations

import importlib
import sys

VIEWER_HINT = 'maxitor-api needs the viewer: pip install "maxitor[viewer]"'


def _brought_by_viewer(error: ModuleNotFoundError) -> bool:
    """Whether the missing module is one the ``viewer`` extra installs."""
    brought = {"aoa", "fastapi", "starlette", "uvicorn", "duckdb", "httpx", "websockets"}
    return (error.name or "").split(".")[0] in brought


def viewer() -> None:
    """
    AI-CORE-BEGIN
    ROLE: Entry point of the ``maxitor-api`` command: run Maxitor's server.
    CONTRACT: Without the ``viewer`` extra, writes ``VIEWER_HINT`` to standard error and exits 2; any other error propagates.
    AI-CORE-END
    """
    try:
        main = importlib.import_module("maxitor.viewer.api.main")
    except ModuleNotFoundError as error:
        if not _brought_by_viewer(error):
            raise
        sys.stderr.write(VIEWER_HINT + "\n")
        raise SystemExit(2) from None
    main.run()
