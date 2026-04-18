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


class TicketStubParams(BaseParams):
    subject: str = Field(description="Ticket subject")


class TicketStubResult(BaseResult):
    ticket_id: str = Field(description="Stub ticket id")


@meta(description="Open support ticket stub (support sample)", domain=SupportDomain)
@check_roles(NoneRole)
class TicketStubAction(BaseAction[TicketStubParams, TicketStubResult]):
    @summary_aspect("Open")
    async def open_summary(
        self,
        params: TicketStubParams,
        state: Any,
        box: Any,
        connections: Any,
    ) -> TicketStubResult:
        return TicketStubResult(ticket_id=f"T-{len(params.subject):04d}")
