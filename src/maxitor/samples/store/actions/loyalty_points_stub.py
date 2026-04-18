# src/maxitor/samples/store/actions/loyalty_points_stub.py
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
from maxitor.samples.store.domain import StoreDomain


class LoyaltyPointsStubParams(BaseParams):
    customer_id: str = Field(description="Customer id")


class LoyaltyPointsStubResult(BaseResult):
    points: int = Field(description="Stub balance", ge=0)


@meta(description="Fetch loyalty points balance (store sample stub)", domain=StoreDomain)
@check_roles(NoneRole)
class LoyaltyPointsStubAction(BaseAction[LoyaltyPointsStubParams, LoyaltyPointsStubResult]):
    @summary_aspect("Points")
    async def points_summary(
        self,
        params: LoyaltyPointsStubParams,
        state: Any,
        box: Any,
        connections: Any,
    ) -> LoyaltyPointsStubResult:
        return LoyaltyPointsStubResult(points=len(params.customer_id) * 7)
