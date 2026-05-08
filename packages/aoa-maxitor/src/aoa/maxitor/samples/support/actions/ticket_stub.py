# packages/aoa-maxitor/src/aoa/maxitor/samples/support/actions/ticket_stub.py
from __future__ import annotations

from typing import Any

from pydantic import Field

from aoa.action_machine.auth import NoneRole
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.maxitor.samples.support.domain import SupportDomain


@meta(description="Open support ticket stub (support sample)", domain=SupportDomain)
@check_roles(NoneRole)
class TicketStubAction(BaseAction["TicketStubAction.Params", "TicketStubAction.Result"]):
    class Params(BaseParams):
        subject: str = Field(description="Ticket subject")

    class Result(BaseResult):
        ticket_id: str = Field(description="Stub ticket id")

    @summary_aspect("Open")
    async def open_summary(
        self,
        params: TicketStubAction.Params,
        state: Any,
        box: Any,
        connections: Any,
    ) -> TicketStubAction.Result:
        return TicketStubAction.Result(ticket_id=f"T-{len(params.subject):04d}")
