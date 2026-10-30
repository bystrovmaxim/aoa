# packages/maxitor/front/src/maxitor/front/model/core/history_reading.py
"""
History reading — open a history through its port and hold it, the steps the history actions share.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Opening a history and reading its list again after the 30 seconds an acceptance lasts
are the same steps: ask the port to describe the history and list its versions with the
reader's key, turn a refusal into its fixed answer, and hold what came back (spec 037,
FR-003, FR-009, FR-011e). These functions are those steps; the actions call them from
their aspects, with the resources they were given.

Every refusal of a private history is a security warning naming the port's origin, the
history's id and the reader's address — never the key (FR-011e).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    name + key ──history_from_name──► history ──port_route──► (route, link)
        ──gateway.describe──► Described ──gateway.versions──► Listed ──► HistoryEntry held, key accepted
               └─ PortNotFound ──► security warning ──► HistoryNotFoundError
               └─ PortTooManyWrongKeys ──► security warning ──► TooManyWrongKeysError
               └─ PortUnreachable ──► business warning (the port's label) ──► HistoryUnreachableError
"""

from __future__ import annotations

from typing import NoReturn

from maxitor.front.model.core.history_address import PrivateHistory, PublicHistory, history_from_name, port_route
from maxitor.front.model.core.history_entry import HistoryEntry, short_sha
from maxitor.front.model.core.history_errors import HistoryNotFoundError, HistoryUnreachableError, TooManyWrongKeysError
from maxitor.front.model.core.resources.graph_source_gateway import Document, GraphSourceGateway
from maxitor.front.model.core.resources.history_access import HistoryAccess
from maxitor.front.model.core.resources.history_store import HistoryStore
from maxitor.front.model.core.resources.repo_graph_port_gateway import (
    Described,
    Listed,
    PortNotFound,
    PortNotModified,
    PortTooManyWrongKeys,
    PortUnreachable,
    RepoGraphPortGateway,
)
from maxitor.front.model.core.same_graph import same_graph
from maxitor.front.model.core.source_label import label

from aoa.action_machine.logging import Channel
from aoa.action_machine.runtime.tools_box import ToolsBox


def _host_of(repository: str, history: PrivateHistory | PublicHistory) -> str:
    """``github`` for a repository named ``owner/name`` or a public link; ``local`` for a path on the port's disk."""
    if isinstance(history, PublicHistory):
        return "github"
    return "local" if repository.startswith(("/", ".", "~")) or "\\" in repository else "github"


def history_line(entry: HistoryEntry) -> str:
    """How the log names a history: by its id and the key's name, or as a public repository."""
    if entry.public:
        return f"history public {entry.title}"
    return f"history {entry.title} by {entry.reader or 'an unnamed key'}"


async def refuse(
    box: ToolsBox,
    outcome: PortNotFound | PortTooManyWrongKeys | PortUnreachable | PortNotModified,
    history: PrivateHistory | PublicHistory,
    route: str,
    client: str,
) -> NoReturn:
    """Log a port's refusal and raise its fixed answer; a refusal of a private history is a security warning."""
    if isinstance(outcome, PortUnreachable | PortNotModified):
        reason = outcome.reason if isinstance(outcome, PortUnreachable) else "an unexpected 304"
        await box.warning(Channel.business, "History {%var.history} at {%var.port} cannot be read now: {%var.reason}", history=history.title, port=label(route), reason=reason)
        raise HistoryUnreachableError()
    if isinstance(history, PrivateHistory):
        if isinstance(outcome, PortTooManyWrongKeys):
            await box.warning(Channel.security, "History {%var.history} at {%var.port} blocked Maxitor for too many wrong keys; the last came from {%var.client}", history=history.id, port=label(history.port), client=client or "unknown")
        else:
            await box.warning(Channel.security, "History {%var.history} at {%var.port} refused the key from {%var.client}", history=history.id, port=label(history.port), client=client or "unknown")
    if isinstance(outcome, PortTooManyWrongKeys):
        raise TooManyWrongKeysError()
    raise HistoryNotFoundError()


async def open_history(
    box: ToolsBox,
    gateway: RepoGraphPortGateway,
    store: HistoryStore,
    access: HistoryAccess,
    name: str,
    key: str,
    client: str,
) -> HistoryEntry:
    """
    AI-CORE-BEGIN
    ROLE: Read a history from its port with the reader's key, and hold it.
    CONTRACT: Returns the held entry, the key remembered and accepted; a refusal raises ``HistoryNotFoundError``, ``TooManyWrongKeysError`` or ``HistoryUnreachableError`` after logging it; an address out of shape raises ``HistoryAddressError`` or ``PublicHistoriesNotSetUpError``.
    INVARIANTS: The key goes only to the gateway and into the entry's in-memory keys; no log line names it.
    AI-CORE-END
    """
    history = history_from_name(name, key)
    route, link = port_route(history, gateway.public_port)
    described = await gateway.describe(route, link, key)
    if not isinstance(described, Described):
        await refuse(box, described, history, route, client)
    listed = await gateway.versions(route, link, key, None)
    if not isinstance(listed, Listed):
        await refuse(box, listed, history, route, client)
    body = described.body
    held = store.peek(history.name)
    entry = HistoryEntry(
        name=history.name,
        route=route,
        link=link,
        title=history.title,
        repository=str(body.get("repository") or ""),
        host=_host_of(str(body.get("repository") or ""), history),
        live=body.get("live") if isinstance(body.get("live"), str) and isinstance(history, PrivateHistory) else None,
        reader=body.get("reader") if isinstance(body.get("reader"), str) else None,
        versions=listed.versions,
        proposals=listed.proposals,
        etag=listed.etag,
        last_checked=store.now(),
        keys=list(held.keys) if held is not None else [],
    )
    if isinstance(history, PrivateHistory):
        entry.remember(key)
        access.accept(history.name, key)
    store.put(entry)
    return entry


async def live_same_as(entry: HistoryEntry, graphs: GraphSourceGateway, key: str) -> str | None:
    """
    AI-CORE-BEGIN
    ROLE: Find whether Live is the newest version: the same graph.
    CONTRACT: The newest version's full sha when the history has Live and its graph is the newest unrefused version's graph; ``None`` otherwise, or when either cannot be read. Never raises.
    INVARIANTS: The key goes only to the port, as the version download's header.
    AI-CORE-END
    """
    newest = next((version for version in reversed(entry.versions) if not version.get("refused")), None)
    if entry.live is None or newest is None:
        return None
    source = entry.source_of(short_sha(str(newest["sha"])))
    if source is None:
        return None
    live = await graphs.fetch(entry.live)
    version = await graphs.with_key(key).fetch(source)
    if not isinstance(live, Document) or not isinstance(version, Document):
        return None
    return str(newest["sha"]) if same_graph(live.body, version.body) else None
