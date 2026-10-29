# packages/maxitor/tools/repo_graph_port/src/maxitor/repo_graph_port/actions/report_security_event_action.py
"""
ReportSecurityEventAction — write one security event of the port to its log.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The port refuses a wrong key, a webhook with a wrong signature, and a client that
sent too many wrong keys. Each refusal leaves a trace on the ``security`` channel, so
whoever runs the port sees who tried what: a warning for a wrong key or signature, a
critical line for a block. The places that refuse — the auth coordinator and the
webhook's middleware — run outside an action, so they hand the event to this action,
which writes it through its ``box``. Nothing secret is written: the client's address
and the history's id, never the key, its hash or the signature.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    coordinator / middleware ──SecurityReporter.report(kind, client, history, count)──► this action
        wrong_key     ──► box.warning(security)  "Wrong key for history <id> from <client>"
        bad_signature ──► box.warning(security)  "Webhook with a wrong signature from <client>"
        blocked       ──► box.critical(security) "Blocked <client> for a minute: <n> wrong keys"
"""

from __future__ import annotations

from typing import Literal

from maxitor.repo_graph_port.repo_graph_domain import RepoGraphDomain
from pydantic import Field

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.logging import Channel
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult, BaseState
from aoa.action_machine.resources import Connections
from aoa.action_machine.runtime.tools_box import ToolsBox

#: What a security event can be.
SecurityEventKind = Literal["wrong_key", "bad_signature", "blocked"]


class ReportSecurityEventParams(BaseParams):
    """One refusal to write down."""

    kind: SecurityEventKind = Field(description="What was refused")
    client: str = Field(description="The client's address")
    history: str = Field(default="", description="The history's id the wrong key was sent for; empty when none was named")
    count: int = Field(default=0, ge=0, description="How many wrong keys the client sent within the minute, for a block")


class ReportSecurityEventResult(BaseResult):
    """Nothing comes back: the event is in the log."""


@meta(description="Write one security event of the port to its log", domain=RepoGraphDomain)
@check_roles(GuestRole)
class ReportSecurityEventAction(BaseAction[ReportSecurityEventParams, ReportSecurityEventResult]):
    """
    AI-CORE-BEGIN
    ROLE: The one place a security event of the port is written to its log.
    CONTRACT: ``wrong_key`` and ``bad_signature`` are a ``warning`` on ``Channel.security``; ``blocked`` is a ``critical`` on it.
    INVARIANTS: Writes the client's address, the history's id and the count; never a key, a hash or a signature, which it is never given.
    AI-CORE-END
    """

    @summary_aspect("Write the event")
    async def report_summary(
        self,
        params: ReportSecurityEventParams,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> ReportSecurityEventResult:
        """Write the event at its level."""
        _ = (state, connections)
        if params.kind == "wrong_key":
            await box.warning(Channel.security, "Wrong key for history {%var.history} from {%var.client}", history=params.history or "(none named)", client=params.client)
        elif params.kind == "bad_signature":
            await box.warning(Channel.security, "Webhook with a wrong signature from {%var.client}", client=params.client)
        else:
            await box.critical(Channel.security, "Blocked {%var.client} for a minute: {%var.count} wrong keys", client=params.client, count=params.count)
        return ReportSecurityEventResult()
