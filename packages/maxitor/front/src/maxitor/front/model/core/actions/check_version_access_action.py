# packages/maxitor/front/src/maxitor/front/model/core/actions/check_version_access_action.py
"""
CheckVersionAccessAction — decide whether a reader may read a version's graph, before it is handed over.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A version's graph is built once and shared by every reader (spec 037, FR-005), but only
a reader whose key the port accepts may read it (FR-009). Before a diagram read of a
version, ``GraphSourceMiddleware`` runs this action: a public history is open to all; a
private one needs the reader's key to have been accepted by the port within 30 seconds,
or the port is asked again now. A version the history does not list is not found; one
whose graph the port refused carries the port's reason (FR-008).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    source ──parse_version_source──► (name, sha) ──► held history? ──no──► HistoryNotFoundError
        private, key not accepted lately ──► port.versions(key, etag) ──► accepted | refused (logged)
        the version listed? ──no──► HistoryNotFoundError
        refused by the schema? ──► VersionRefusedError(reason)
"""

from __future__ import annotations

from typing import cast

from maxitor.front.model.core.core_domain import CoreDomain
from maxitor.front.model.core.history_address import PrivateHistory, history_from_name, parse_version_source
from maxitor.front.model.core.history_errors import HistoryNotFoundError
from maxitor.front.model.core.history_reading import refuse
from maxitor.front.model.core.resources.history_access import HISTORY_ACCESS_CONNECTION_KEY, HistoryAccess
from maxitor.front.model.core.resources.history_store import HISTORY_STORE_CONNECTION_KEY, HistoryStore
from maxitor.front.model.core.resources.repo_graph_port_gateway import (
    REPO_GRAPH_PORT_CONNECTION_KEY,
    Listed,
    PortNotModified,
    RepoGraphPortGateway,
)
from pydantic import Field

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.context.context_view import ContextView
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.connection import connection
from aoa.action_machine.intents.context_requires import context_requires
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult, BaseState
from aoa.action_machine.resources import Connections
from aoa.action_machine.runtime.tools_box import ToolsBox


class VersionRefusedError(ValueError):
    """The version's graph does not pass the protocol's schema; the message is the port's reason."""


class CheckVersionAccessParams(BaseParams):
    """The version source a diagram read names."""

    source: str = Field(min_length=1, description="A version's source: the port's version URL, keyless")


class CheckVersionAccessResult(BaseResult):
    """The reader may read the version."""


@meta(description="Decide whether a reader may read a version's graph", domain=CoreDomain)
@check_roles(GuestRole)
@connection(RepoGraphPortGateway, key=REPO_GRAPH_PORT_CONNECTION_KEY, description="Asks the port whether a key still opens the history")
@connection(HistoryStore, key=HISTORY_STORE_CONNECTION_KEY, description="The histories Maxitor holds")
@connection(HistoryAccess, key=HISTORY_ACCESS_CONNECTION_KEY, description="Keys the port accepted lately")
class CheckVersionAccessAction(BaseAction[CheckVersionAccessParams, CheckVersionAccessResult]):
    """
    AI-CORE-BEGIN
    ROLE: Let a version's graph go only to a reader the port lets read its history.
    CONTRACT: Returns when the reader may read; raises ``HistoryNotFoundError`` (unknown history or version, a key the port refuses), ``TooManyWrongKeysError``, ``HistoryUnreachableError`` or ``VersionRefusedError``.
    INVARIANTS: Asks the port at most once per key per 30 seconds; a refusal of a key is a security warning.
    AI-CORE-END
    """

    @summary_aspect("Decide whether the reader may read the version")
    @context_requires("user.history_key", "request.client_ip")
    async def access_summary(
        self,
        params: CheckVersionAccessParams,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
        ctx: ContextView,
    ) -> CheckVersionAccessResult:
        """Check the key, then the version."""
        _ = state
        named = parse_version_source(params.source)
        store = cast(HistoryStore, connections[HISTORY_STORE_CONNECTION_KEY])
        entry = store.peek(named[0]) if named is not None else None
        if named is None or entry is None:
            raise HistoryNotFoundError()
        key = str(ctx.get("user.history_key") or "")
        access = cast(HistoryAccess, connections[HISTORY_ACCESS_CONNECTION_KEY])
        if not entry.public and not access.accepted(entry.name, key):
            history = history_from_name(entry.name, key)
            gateway = cast(RepoGraphPortGateway, connections[REPO_GRAPH_PORT_CONNECTION_KEY])
            answer = await gateway.versions(entry.route, entry.link, key, entry.etag)
            if not isinstance(answer, Listed | PortNotModified):
                if isinstance(history, PrivateHistory):
                    entry.forget(key)
                await refuse(box, answer, history, entry.route, str(ctx.get("request.client_ip") or ""))
            access.accept(entry.name, key)
            entry.remember(key)
        version = entry.version(named[1])
        if version is None:
            raise HistoryNotFoundError()
        if version.get("refused"):
            raise VersionRefusedError(str(version["refused"]))
        return CheckVersionAccessResult()
