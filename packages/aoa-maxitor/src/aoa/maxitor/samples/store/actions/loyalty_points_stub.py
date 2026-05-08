# packages/aoa-maxitor/src/aoa/maxitor/samples/store/actions/loyalty_points_stub.py
from __future__ import annotations

from typing import Any

from pydantic import Field

from aoa.action_machine.auth import NoneRole
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.maxitor.samples.store.domain import StoreDomain


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
