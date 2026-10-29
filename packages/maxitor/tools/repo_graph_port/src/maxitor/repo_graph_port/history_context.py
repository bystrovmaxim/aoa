# packages/maxitor/tools/repo_graph_port/src/maxitor/repo_graph_port/history_context.py
"""
HistoryContext — the context a history is read in, with the environment the actions declare.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

How often a history fetches its repository when no webhook says it changed comes
from the environment; the actions read it only through the context they declare
(``@context_requires("env.history_refresh_seconds")``), never from ``os.environ``.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

``MAXITOR_HISTORY_REFRESH_SECONDS`` (default 600) ──@env──► ``env.history_refresh_seconds``
──► ``HistoryAction`` decides whether to fetch before it answers.
"""

from __future__ import annotations

import os
from collections.abc import Callable

from aoa.action_machine.context import Context, env


def _refresh_seconds() -> int:
    """Seconds after which a history fetches its repository again without a webhook."""
    return int(os.environ.get("MAXITOR_HISTORY_REFRESH_SECONDS", "600"))


# ``@env`` takes a provider or a constant; naming the union lets the type checker see the value is an ``int``.
_REFRESH_SECONDS: Callable[[], int] | int = _refresh_seconds


@env("history_refresh_seconds", _REFRESH_SECONDS, ttl=60)
class HistoryContext(Context):
    """
    AI-CORE-BEGIN
    ROLE: The context a history is read in.
    CONTRACT: ``env.history_refresh_seconds`` — the fallback fetch interval, from ``MAXITOR_HISTORY_REFRESH_SECONDS`` (default 600), reread every minute.
    AI-CORE-END
    """
