# packages/maxitor/tools/repo_graph_port/src/maxitor/repo_graph_port/server.py
"""
The port's own HTTP server: its actions under ``/api/v1/history/``.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The port is a service of its own (``https://repo-graph-port.aoa.run`` on the stand):
Maxitor and any other client read histories from it over HTTP, and only it talks to
the host. ``create_app`` builds that server from the histories config and the cache
folder, with every route an action behind ``FastApiAdapter``.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    MAXITOR_HISTORIES ──► HistoriesConfig ─┐
    MAXITOR_HISTORY_CACHE ──► GitMirror, VersionCache ─┼─► FastApiAdapter(HistoryKeyAuthCoordinator)
                                                        │      /api/v1/history/public…?link=   (no key)
                                                        │      /api/v1/history/{history}…       (its key)
                                                        │      POST /api/v1/history/events/github (GitHub's webhook)
                                                        ├─► VersionFileMiddleware (a version as its file)
                                                        └─► WebhookSignatureMiddleware (only a signed body reaches the webhook)

A refusal of any kind is ``404 {"detail": "not found"}``; too many wrong keys from one
client are ``429``. ``history`` answers carry an ``ETag`` and a repeated read naming it
is ``304`` (the adapter's conditional GET). ``/health`` answers when the server is up.
The environment is read here, where the server is built — never in an action.
"""

from __future__ import annotations

import os
from importlib.metadata import version
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from maxitor.repo_graph_port.actions.describe_history_action import DescribeHistoryAction
from maxitor.repo_graph_port.actions.history_action import HistoryAction
from maxitor.repo_graph_port.actions.receive_host_event_action import ReceiveHostEventAction
from maxitor.repo_graph_port.actions.version_action import VersionAction
from maxitor.repo_graph_port.auth.history_key_auth_coordinator import HistoryKeyAuthCoordinator
from maxitor.repo_graph_port.github_event import GitHubEvent
from maxitor.repo_graph_port.history_not_found_error import HistoryNotFoundError
from maxitor.repo_graph_port.resources.git_mirror import GitMirror
from maxitor.repo_graph_port.resources.github_host import GitHubHost
from maxitor.repo_graph_port.resources.histories_config import HistoriesConfig
from maxitor.repo_graph_port.resources.version_cache import VersionCache
from maxitor.repo_graph_port.too_many_wrong_keys_error import TooManyWrongKeysError
from maxitor.repo_graph_port.version_file_middleware import VersionFileMiddleware
from maxitor.repo_graph_port.webhook_signature_middleware import WebhookSignatureMiddleware

from aoa.action_machine.graph.node_graph_coordinator_factory import create_node_graph_coordinator
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.fastapi import FastApiAdapter


def create_app(histories: Path | None = None, cache: Path | None = None, host: GitHubHost | None = None) -> FastAPI:
    """
    AI-CORE-BEGIN
    ROLE: Build the port's server.
    CONTRACT: ``histories`` defaults to ``$MAXITOR_HISTORIES`` (required), ``cache`` to ``$MAXITOR_HISTORY_CACHE`` or ``~/.cache/maxitor/history``; ``host`` defaults to GitHub as the config's ``[github]`` names it, its private key and webhook secret read from the variables it names; a config out of shape raises ``ValueError`` before the server exists.
    INVARIANTS: Every route is an action; the App's secrets and the keys never reach a log.
    AI-CORE-END
    """
    config_path = histories or Path(os.environ["MAXITOR_HISTORIES"])
    folder = cache or Path(os.environ.get("MAXITOR_HISTORY_CACHE") or Path.home() / ".cache" / "maxitor" / "history")
    config = HistoriesConfig(config_path)
    github = config.github()
    if host is None:
        app_id, key_variable, secret_variable = github or (None, "", "")
        host = GitHubHost(app_id, os.environ.get(key_variable) or None, os.environ.get(secret_variable) or None)
    connections = {"HistoriesConfig": config, "GitMirror": GitMirror(folder), "VersionCache": VersionCache(folder), "GitHubHost": host}
    adapter = FastApiAdapter(
        machine=ActionProductMachine(graph_coordinator=create_node_graph_coordinator()),
        auth_coordinator=HistoryKeyAuthCoordinator(config),
        title="repo-graph-port",
        version=version("maxitor"),
    )
    # The public routes come first, so ``public`` is never read as a history's id.
    for prefix in ("/api/v1/history/public", "/api/v1/history/{history}"):
        adapter.get(prefix, DescribeHistoryAction, connections=connections)
        adapter.get(f"{prefix}/versions", HistoryAction, connections=connections)
        adapter.get(f"{prefix}/versions/{{sha}}", VersionAction, connections=connections)
    adapter.post("/api/v1/history/events/github", ReceiveHostEventAction, request_model=GitHubEvent, params_mapper=GitHubEvent.as_params, connections=connections)
    app = adapter.build()

    @app.exception_handler(HistoryNotFoundError)
    async def not_found(_request: Request, _error: HistoryNotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": "not found"})

    @app.exception_handler(TooManyWrongKeysError)
    async def too_many(_request: Request, _error: TooManyWrongKeysError) -> JSONResponse:
        return JSONResponse(status_code=429, content={"detail": "too many requests"})

    app.add_middleware(VersionFileMiddleware)
    app.add_middleware(WebhookSignatureMiddleware, verify=host.verify_webhook)
    return app
