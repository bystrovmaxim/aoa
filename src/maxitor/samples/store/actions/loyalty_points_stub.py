# src/maxitor/samples/store/actions/loyalty_points_stub.py
from __future__ import annotations

from typing import Any

from pydantic import Field

from action_machine.auth.none_role import NoneRole
from action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from action_machine.intents.check_roles.check_roles_decorator import check_roles
from action_machine.intents.meta.meta_decorator import meta
from action_machine.model.base_action import BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from maxitor.samples.store.domain import StoreDomain


@meta(description="Fetch loyalty points balance (store sample stub)", domain=StoreDomain)
@check_roles(NoneRole)
class LoyaltyPointsStubAction(BaseAction["LoyaltyPointsStubAction.Params", "LoyaltyPointsStubAction.Result"]):
    class Params(BaseParams):
        customer_id: str = Field(description="Customer id")

    class Result(BaseResult):
        points: int = Field(description="Stub balance", ge=0)

    @summary_aspect("Points")
    async def points_summary(
        self,
        params: LoyaltyPointsStubAction.Params,
        state: Any,
        box: Any,
        connections: Any,
    ) -> LoyaltyPointsStubAction.Result:
        return LoyaltyPointsStubAction.Result(points=len(params.customer_id) * 7)
