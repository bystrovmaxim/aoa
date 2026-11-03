# packages/aoa-demo/src/aoa/demo/model/store/actions/return_approve.py
from __future__ import annotations

from pydantic import Field

from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult, BaseState
from aoa.action_machine.resources import Connections
from aoa.action_machine.runtime.tools_box import ToolsBox
from aoa.demo.model.roles import EditorRole
from aoa.demo.model.store.store_domain import StoreDomain


@meta(description="Approve a customer's return so it can be refunded (store sample stub)", domain=StoreDomain)
@check_roles(EditorRole)
class ReturnApproveAction(BaseAction["ReturnApproveAction.Params", "ReturnApproveAction.Result"]):
    class Params(BaseParams):
        return_id: str = Field(description="Return request to approve")

    class Result(BaseResult):
        approved: bool = Field(description="Whether the return was approved")

    @summary_aspect("Approve return")
    async def approve_summary(
        self,
        params: ReturnApproveAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> ReturnApproveAction.Result:
        return ReturnApproveAction.Result(approved=bool(params.return_id))
