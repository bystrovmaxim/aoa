# packages/maxitor/tools/repo_graph_port/src/maxitor/repo_graph_port/auth/history_key_authenticator.py
"""
HistoryKeyAuthenticator — a key's holder and the history it opens, found by the key's hash.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The config keeps only each key's SHA-256. A key is hashed and looked up by its
hash; when it is known and not expired, the request reads as its holder — the key's
name — with ``HistoryReaderRole`` and the one history the key opens.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

``{"key": …}`` ──sha256──► ``HistoriesConfig.reader_of(hash, today)`` ──► ``HistoryReaderInfo`` | ``None``.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any

from maxitor.repo_graph_port.history_reader_info import HistoryReaderInfo
from maxitor.repo_graph_port.history_reader_role import HistoryReaderRole
from maxitor.repo_graph_port.resources.histories_config import HistoriesConfig

from aoa.action_machine.auth.authenticator import Authenticator


class HistoryKeyAuthenticator(Authenticator):
    """
    AI-CORE-BEGIN
    ROLE: Turn a read key into its holder and the history it opens.
    CONTRACT: A known, unexpired key → ``HistoryReaderInfo(user_id=<name>, roles=(HistoryReaderRole,), history=<id>)``; any other → ``None``.
    INVARIANTS: Compares hashes only; never keeps or shows the key.
    AI-CORE-END
    """

    def __init__(self, config: HistoriesConfig) -> None:
        self._config = config

    def __repr__(self) -> str:
        """Name the config, never a key."""
        return f"HistoryKeyAuthenticator({self._config!r})"

    async def authenticate(self, credentials: Any) -> HistoryReaderInfo | None:
        """The holder of ``credentials["key"]``, or ``None``."""
        key = credentials.get("key") if isinstance(credentials, dict) else None
        if not isinstance(key, str) or not key:
            return None
        found = self._config.reader_of(hashlib.sha256(key.encode()).hexdigest(), datetime.now(UTC).date())
        if found is None:
            return None
        history_id, name = found
        return HistoryReaderInfo(user_id=name, roles=(HistoryReaderRole,), history=history_id)
