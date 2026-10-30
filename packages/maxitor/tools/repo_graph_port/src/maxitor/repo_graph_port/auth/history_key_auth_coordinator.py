# packages/maxitor/tools/repo_graph_port/src/maxitor/repo_graph_port/auth/history_key_auth_coordinator.py
"""
HistoryKeyAuthCoordinator — who a request reads as, and the limit on wrong keys.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Every request reaches its action: with a valid key as the key's holder, otherwise
as a guest, who can open only public links — so a missing, unknown, revoked or
expired key ends in the action's one answer, "not found", never in a different
one that would tell a stranger which keys exist. Once a client address has sent more
than the limit of keys that open nothing within a minute, each further wrong key from
it is refused with "too many requests".

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    request ──extract──► no key ──────────────────────────► HistoryContext(guest)
                     └─► key ──authenticate──► holder ────► HistoryContext(holder, history)
                                         └──► none ──count──► over the limit? ──► TooManyWrongKeysError (429)
                                                                     └─ no ──► HistoryContext(guest)

Every wrong key is reported as a security warning; the key that passes the limit, as a
critical block (``SecurityReporter``). Neither names the key.

The context is ``HistoryContext``, which carries the environment the actions declare.
"""

from __future__ import annotations

import re
import time
from collections import deque
from typing import Any

from maxitor.repo_graph_port.auth.history_key_authenticator import HistoryKeyAuthenticator
from maxitor.repo_graph_port.auth.history_key_credential_extractor import HistoryKeyCredentialExtractor
from maxitor.repo_graph_port.history_context import HistoryContext
from maxitor.repo_graph_port.history_reader_info import HistoryReaderInfo
from maxitor.repo_graph_port.resources.histories_config import HistoriesConfig
from maxitor.repo_graph_port.security_reporter import SecurityReporter
from maxitor.repo_graph_port.too_many_wrong_keys_error import TooManyWrongKeysError

from aoa.action_machine.auth.auth_coordinator import AuthCoordinator
from aoa.action_machine.auth.jwt_auth.http_context_assembler import HttpContextAssembler
from aoa.action_machine.context import RequestInfo


class HistoryKeyAuthCoordinator(AuthCoordinator):
    """
    AI-CORE-BEGIN
    ROLE: Give every request its reader: a key's holder, or a guest.
    CONTRACT: ``process`` never returns ``None``; a valid key gives its holder and history, anything else a guest; more than the limit of wrong keys from one client address in a minute raises ``TooManyWrongKeysError``.
    INVARIANTS: Never logs, keeps or shows a key; wrong keys are counted by client address only; each wrong key and each block is handed to the ``SecurityReporter``, when there is one.
    AI-CORE-END
    """

    def __init__(self, config: HistoriesConfig, reporter: SecurityReporter | None = None) -> None:
        super().__init__(
            HistoryKeyCredentialExtractor(),
            HistoryKeyAuthenticator(config),
            HttpContextAssembler(),
            context_class=HistoryContext,
        )
        self._wrong: dict[str, deque[float]] = {}
        self._reporter = reporter

    def __repr__(self) -> str:
        """Name the authenticator, never a key."""
        return f"HistoryKeyAuthCoordinator({self.authenticator!r})"

    async def process(self, request_data: Any) -> HistoryContext:
        """The reader of ``request_data``."""
        request = RequestInfo(**await self.assembler.assemble(request_data))
        credentials = await self.extractor.extract(request_data)
        holder = await self.authenticator.authenticate(credentials) if credentials else None
        if credentials and holder is None:
            await self._count_wrong(request.client_ip or "", _history_of(request.request_path or ""))
        return HistoryContext(user=holder or HistoryReaderInfo(), request=request)

    async def _count_wrong(self, client: str, history: str) -> None:
        """Count and report one wrong key from ``client``; refuse it once it passes the limit within a minute."""
        limit, window_seconds = 10, 60.0
        now = time.monotonic()
        recent = self._wrong.setdefault(client, deque())
        while recent and now - recent[0] > window_seconds:
            recent.popleft()
        recent.append(now)
        if self._reporter is not None:
            await self._reporter.report("wrong_key", client, history)
            if len(recent) == limit + 1:
                await self._reporter.report("blocked", client, history, len(recent))
        if len(recent) > limit:
            raise TooManyWrongKeysError()


def _history_of(path: str) -> str:
    """The history's id a request's path names, or an empty string for a public link or no history."""
    named = re.match(r"/api/v1/history/([^/]+)", path)
    return "" if named is None or named.group(1) == "public" else named.group(1)
