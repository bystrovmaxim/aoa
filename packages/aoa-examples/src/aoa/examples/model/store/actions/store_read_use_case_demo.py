# packages/aoa-examples/src/aoa/examples/model/store/actions/store_read_use_case_demo.py
"""Graph-only demo: same-domain ``UseCase.include`` / ``UseCase.extend`` between store read actions."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.depends import UseCase, depends
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.examples.model.roles import ViewerRole
from aoa.examples.model.store.actions.order_lookup import OrderLookupAction
from aoa.examples.model.store.actions.store_read import StoreReadAction
from aoa.examples.model.store.store_domain import StoreDomain


@meta(
    description="Demo orchestrator: @depends include/extend on store read actions (Maxitor use-case diagram)",
    domain=StoreDomain,
)
@check_roles(ViewerRole)
@depends(
    OrderLookupAction,
    mode=UseCase.extend,
    description="Optional order-lookup specialization",
)
@depends(
    StoreReadAction,
    mode=UseCase.include,
    description="Base store read is always included",
)
class StoreReadUseCaseDemoAction(BaseAction["StoreReadUseCaseDemoAction.Params", "StoreReadUseCaseDemoAction.Result"]):
    class Params(BaseParams):
        placeholder: str = Field(default="", description="Unused; graph demo only")

    class Result(BaseResult):
        note: str = Field(default="demo", description="Stub; graph demo only")

    @summary_aspect("Stub summary for use-case demo action")
    async def demo_summary(
        self,
        params: StoreReadUseCaseDemoAction.Params,
        state: Any,
        box: Any,
        connections: Any,
    ) -> StoreReadUseCaseDemoAction.Result:
        _ = (params, state, connections)
        await box.run(StoreReadAction, StoreReadAction.Params())
        return StoreReadUseCaseDemoAction.Result()
