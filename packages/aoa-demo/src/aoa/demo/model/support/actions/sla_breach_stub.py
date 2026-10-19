# packages/aoa-demo/src/aoa/demo/model/support/actions/sla_breach_stub.py
from __future__ import annotations

from pydantic import Field

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult, BaseState
from aoa.action_machine.resources import Connections
from aoa.action_machine.runtime.tools_box import ToolsBox
from aoa.demo.model.support.support_domain import SupportDomain


@meta(description="Evaluate SLA breach (support sample stub)", domain=SupportDomain)
@check_roles(GuestRole)
class SlaBreachStubAction(BaseAction["SlaBreachStubAction.Params", "SlaBreachStubAction.Result"]):
    class Params(BaseParams):
        ticket_id: str = Field(description="Ticket id")

    class Result(BaseResult):
        breached: bool = Field(description="Stub breach flag")

    @summary_aspect("Evaluate")
    async def evaluate_summary(
        self,
        params: SlaBreachStubAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> SlaBreachStubAction.Result:
        return SlaBreachStubAction.Result(breached=len(params.ticket_id) % 2 == 0)
