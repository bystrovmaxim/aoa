# src/maxitor/samples/support/actions/sla_breach_stub.py
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


class SlaBreachStubParams(BaseParams):
    ticket_id: str = Field(description="Ticket id")


class SlaBreachStubResult(BaseResult):
    breached: bool = Field(description="Stub breach flag")


@meta(description="Evaluate SLA breach (support sample stub)", domain=SupportDomain)
@check_roles(NoneRole)
class SlaBreachStubAction(BaseAction[SlaBreachStubParams, SlaBreachStubResult]):
    @summary_aspect("Evaluate")
    async def evaluate_summary(
        self,
        params: SlaBreachStubParams,
        state: Any,
        box: Any,
        connections: Any,
    ) -> SlaBreachStubResult:
        return SlaBreachStubResult(breached=len(params.ticket_id) % 2 == 0)
