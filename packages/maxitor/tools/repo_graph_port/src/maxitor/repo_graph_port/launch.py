# packages/maxitor/tools/repo_graph_port/src/maxitor/repo_graph_port/launch.py
"""
The command ``repo-graph-port``: serve the port, or administer its keys.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

One command for the service: with no arguments it serves the port; ``history …``
runs the key commands. The code is in every ``maxitor`` wheel, but only the extra
``repo-graph-port`` brings its dependencies; without them the command says which
extra to install instead of failing on an import.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

``repo-graph-port``                → uvicorn on ``$REPO_GRAPH_PORT_HOST:$REPO_GRAPH_PORT_PORT`` (default ``127.0.0.1:8102``)
``repo-graph-port history …``      → ``maxitor.repo_graph_port.cli``

A ``ModuleNotFoundError`` for a dependency the extra brings becomes one line on
standard error and exit code 2; any other error propagates. Nothing heavy is
imported at module level, so this module loads without the extra.
"""

from __future__ import annotations

import importlib
import os
import sys

PORT_HINT = 'repo-graph-port needs its extra: pip install "maxitor[repo-graph-port]"'


def _brought_by_extra(error: ModuleNotFoundError) -> bool:
    """Whether the missing module is one the ``repo-graph-port`` extra installs."""
    brought = {"aoa", "fastapi", "starlette", "uvicorn", "jwt", "httpx"}
    return (error.name or "").split(".")[0] in brought


def main() -> None:
    """
    AI-CORE-BEGIN
    ROLE: Entry point of the ``repo-graph-port`` command.
    CONTRACT: No arguments → serve; ``history …`` → the key commands, exiting with their code. Without the extra, writes ``PORT_HINT`` to standard error and exits 2.
    AI-CORE-END
    """
    arguments = sys.argv[1:]
    try:
        if arguments[:1] == ["history"]:
            cli = importlib.import_module("maxitor.repo_graph_port.cli")
            raise SystemExit(cli.main(arguments[1:]))
        server = importlib.import_module("maxitor.repo_graph_port.server")
        uvicorn = importlib.import_module("uvicorn")
    except ModuleNotFoundError as error:
        if not _brought_by_extra(error):
            raise
        sys.stderr.write(PORT_HINT + "\n")
        raise SystemExit(2) from None
    host = os.environ.get("REPO_GRAPH_PORT_HOST", "127.0.0.1")
    port = int(os.environ.get("REPO_GRAPH_PORT_PORT", "8102"))
    uvicorn.run(server.create_app(), host=host, port=port, proxy_headers=True)
