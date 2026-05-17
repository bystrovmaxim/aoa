# packages/aoa-examples/src/aoa/examples/model/store/actions/store_read.py
"""Base read action for storefront samples (PR-6 generalization: ``OrderLookupAction`` specialization)."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.examples.model.roles import ViewerRole
from aoa.examples.model.store.domain import StoreDomain


@meta(description="Shared store read pipeline base (sample inheritance)", domain=StoreDomain)
@check_roles(ViewerRole)
class StoreReadAction(BaseAction["StoreReadAction.Params", "StoreReadAction.Result"]):
    """
    Intermediate **read** action for the store slice.

    ``@summary_aspect`` is **own-class** only for graph resolution on subclasses, so
    concrete reads like :class:`~aoa.examples.model.store.actions.order_lookup.OrderLookupAction`
    supply their own summary; params/result types stay on this base so ``BaseAction[P, R]`` resolves for subclasses.
    """

    class Params(BaseParams):
        """Shared store-read params; ``order_id`` used when loading an order snapshot."""

        order_id: str = Field(default="", description="Order id for lookup reads; empty for generic read")

    class Result(BaseResult):
        ok: bool = Field(default=True, description="Whether the read completed")
        order_id: str = Field(default="", description="Loaded order id when applicable")
        amount: float = Field(default=0.0, description="Loaded amount when applicable")
        status: str = Field(default="", description="Loaded status when applicable")

    @summary_aspect("Default store read summary (specializations override aspects)")
    async def store_read_summary(
        self,
        params: StoreReadAction.Params,
        state: Any,
        box: Any,
        connections: Any,
    ) -> StoreReadAction.Result:
        return StoreReadAction.Result()
