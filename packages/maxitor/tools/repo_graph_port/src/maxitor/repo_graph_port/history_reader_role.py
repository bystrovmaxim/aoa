# packages/maxitor/tools/repo_graph_port/src/maxitor/repo_graph_port/history_reader_role.py
"""
HistoryReaderRole — a reader who presented a valid read key.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A read key opens one configured history. The coordinator gives the reader this
role and names, in the reader's identity, the one history the key opens.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

``X-Maxitor-History-Key`` ──``HistoryKeyAuthCoordinator``──► ``HistoryReaderInfo(roles=(HistoryReaderRole,), history=<id>)``.
"""

from __future__ import annotations

from abc import ABC

from aoa.action_machine.auth import ApplicationRole
from aoa.action_machine.intents.check_roles import RoleMode, role_mode


@role_mode(RoleMode.ALIVE)
class HistoryReaderRole(ApplicationRole, ABC):
    """
    AI-CORE-BEGIN
    ROLE: The role of a reader holding a valid read key.
    CONTRACT: Given only by ``HistoryKeyAuthCoordinator``; the history it opens is ``HistoryReaderInfo.history``.
    AI-CORE-END
    """

    name = "history_reader"
    description = "Holds a read key that opens one configured history"
