# src/maxitor/samples/store/actions/order_lookup.py
from __future__ import annotations

from typing import Any

from pydantic import Field

from action_machine.intents.aspects.regular_aspect_decorator import regular_aspect
from action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from action_machine.intents.auth.check_roles_decorator import check_roles
from action_machine.intents.context.context_requires_decorator import context_requires
from action_machine.intents.context.ctx_constants import Ctx
from action_machine.intents.meta.meta_decorator import meta
from action_machine.model.base_action import BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from maxitor.samples.roles import ViewerRole
from maxitor.samples.store.domain import StoreDomain


class OrderLookupParams(BaseParams):
    order_id: str = Field(description="Order id to load")


class OrderLookupResult(BaseResult):
    order_id: str = Field(description="Loaded order id")
    amount: float = Field(description="Loaded amount")
    status: str = Field(description="Loaded status")


@meta(description="Load order snapshot (stub)", domain=StoreDomain)
@check_roles(ViewerRole)
class OrderLookupAction(BaseAction[OrderLookupParams, OrderLookupResult]):
    @regular_aspect("Load order")
    @context_requires(Ctx.User.user_id, Ctx.Request.request_path)
    async def load_aspect(
        self,
        params: OrderLookupParams,
        state: Any,
        box: Any,
        connections: Any,
        ctx: Any,
    ) -> dict[str, Any]:
        return {
            "order_id": params.order_id,
            "amount": 1.0,
            "status": "ok",
        }

    @summary_aspect("Build read result")
    async def build_result_summary(
        self,
        params: OrderLookupParams,
        state: Any,
        box: Any,
        connections: Any,
    ) -> OrderLookupResult:
        return OrderLookupResult(
            order_id=state.order_id,
            amount=state.amount,
            status=state.status,
        )
