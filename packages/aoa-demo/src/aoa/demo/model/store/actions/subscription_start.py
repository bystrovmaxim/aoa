# packages/aoa-demo/src/aoa/demo/model/store/actions/subscription_start.py
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


@meta(description="Start a subscription on a plan (store sample stub)", domain=StoreDomain)
@check_roles(EditorRole)
class SubscriptionStartAction(BaseAction["SubscriptionStartAction.Params", "SubscriptionStartAction.Result"]):
    class Params(BaseParams):
        customer_id: str = Field(description="Customer id")
        plan_code: str = Field(description="Code of the plan to subscribe to")
        renewal_day: int = Field(default=1, description="Day of the month the subscription renews", ge=1, le=28)

    class Result(BaseResult):
        subscription_id: str = Field(description="Id of the new subscription")

    @summary_aspect("Start subscription")
    async def start_summary(
        self,
        params: SubscriptionStartAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> SubscriptionStartAction.Result:
        return SubscriptionStartAction.Result(subscription_id=f"sub-{params.plan_code.lower()}-{params.customer_id}")
