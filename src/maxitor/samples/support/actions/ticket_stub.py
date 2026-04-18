# src/maxitor/samples/support/actions/ticket_stub.py
from __future__ import annotations

from typing import Any

from pydantic import Field

from action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from action_machine.intents.auth.check_roles_decorator import check_roles
from action_machine.intents.auth.none_role import NoneRole
from action_machine.intents.meta.meta_decorator import meta
from action_machine.model.base_action import BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from maxitor.samples.support.domain import SupportDomain


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
