# packages/aoa-maxitor/src/aoa/maxitor/samples/support/actions/sla_breach_stub.py
from __future__ import annotations

from typing import Any

from pydantic import Field

from aoa.action_machine.auth import NoneRole
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.maxitor.samples.support.domain import SupportDomain


@meta(description="Evaluate SLA breach (support sample stub)", domain=SupportDomain)
@check_roles(NoneRole)
class SlaBreachStubAction(BaseAction["SlaBreachStubAction.Params", "SlaBreachStubAction.Result"]):
    class Params(BaseParams):
        ticket_id: str = Field(description="Ticket id")

    class Result(BaseResult):
        breached: bool = Field(description="Stub breach flag")

    @summary_aspect("Evaluate")
    async def evaluate_summary(
        self,
        params: SlaBreachStubAction.Params,
        state: Any,
        box: Any,
        connections: Any,
    ) -> SlaBreachStubAction.Result:
        return SlaBreachStubAction.Result(breached=len(params.ticket_id) % 2 == 0)
