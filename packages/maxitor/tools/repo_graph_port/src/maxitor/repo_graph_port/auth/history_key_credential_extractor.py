# packages/maxitor/tools/repo_graph_port/src/maxitor/repo_graph_port/auth/history_key_credential_extractor.py
"""
HistoryKeyCredentialExtractor — the read key from its header.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A key travels only in the header ``X-Maxitor-History-Key``, never in a path or a
query string, so no access log on the way keeps it.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

request headers ──► ``{"key": <value>}``, or ``{}`` when the header is absent or blank.
"""

from __future__ import annotations

from typing import Any

from aoa.action_machine.auth.auth_coordinator import CredentialExtractor


class HistoryKeyCredentialExtractor(CredentialExtractor):
    """
    AI-CORE-BEGIN
    ROLE: Take the read key from ``X-Maxitor-History-Key``.
    CONTRACT: Returns ``{"key": value}`` for a non-blank header, ``{}`` otherwise.
    INVARIANTS: Reads no other header, the path or the query.
    AI-CORE-END
    """

    async def extract(self, request_data: Any) -> dict[str, Any]:
        """The key the request carries, or nothing."""
        key = request_data.headers.get("x-maxitor-history-key", "").strip()
        return {"key": key} if key else {}
