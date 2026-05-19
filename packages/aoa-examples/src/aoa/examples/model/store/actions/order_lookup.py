# packages/aoa-examples/src/aoa/examples/model/store/actions/order_lookup.py
from __future__ import annotations

from typing import Any

from aoa.action_machine.context import Ctx
from aoa.action_machine.intents.aspects import regular_aspect, summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.checkers import result_float, result_string
from aoa.action_machine.intents.context_requires import context_requires
from aoa.action_machine.intents.meta import meta
from aoa.examples.model.roles import ViewerRole
from aoa.examples.model.store.actions.store_read import StoreReadAction
from aoa.examples.model.store.store_domain import StoreDomain


@meta(description="Load order snapshot (stub)", domain=StoreDomain)
@check_roles(ViewerRole)
class OrderLookupAction(StoreReadAction):
    @regular_aspect("Load order")
    @result_string("order_id", required=True, not_empty=True)
    @result_float("amount", required=True)
    @result_string("status", required=True, not_empty=True)
    @context_requires(Ctx.User.user_id, Ctx.Request.request_path)
    async def load_aspect(
        self,
        params: StoreReadAction.Params,
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
        params: StoreReadAction.Params,
        state: Any,
        box: Any,
        connections: Any,
    ) -> StoreReadAction.Result:
        _ = (params, box, connections)
        return StoreReadAction.Result(
            ok=True,
            order_id=state.order_id,
            amount=state.amount,
            status=state.status,
        )
