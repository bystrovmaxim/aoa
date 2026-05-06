# src/maxitor/samples/store/actions/cart_abandon_stub.py
from __future__ import annotations

from typing import Any

from pydantic import Field

from action_machine.auth import NoneRole
from action_machine.intents.aspects import summary_aspect
from action_machine.intents.check_roles import check_roles
from action_machine.intents.meta import meta
from action_machine.model import BaseAction, BaseParams, BaseResult
from maxitor.samples.store.domain import StoreDomain


@meta(description="Schedule cart abandonment follow-up (store sample stub)", domain=StoreDomain)
@check_roles(NoneRole)
class CartAbandonStubAction(BaseAction["CartAbandonStubAction.Params", "CartAbandonStubAction.Result"]):
    class Params(BaseParams):
        session_id: str = Field(description="Checkout session id")

    class Result(BaseResult):
        scheduled: bool = Field(description="Stub schedule flag")

    @summary_aspect("Schedule")
    async def schedule_summary(
        self,
        params: CartAbandonStubAction.Params,
        state: Any,
        box: Any,
        connections: Any,
    ) -> CartAbandonStubAction.Result:
        return CartAbandonStubAction.Result(scheduled=bool(params.session_id))
