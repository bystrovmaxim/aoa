# packages/aoa-examples/src/aoa/examples/model/support/actions/depend_cross_domain_action.py
"""DependCrossDomainAction — resolves a store peer via ``@depends``."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from aoa.action_machine.auth import NoneRole
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.depends import UseCase, depends
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.examples.model.store.actions.ping import OpsPingAction
from aoa.examples.model.support.support_domain import SupportDomain


@meta(
    description="Resolves an action from StoreDomain via @depends (graph: cross-domain)",
    domain=SupportDomain,
)
@check_roles(NoneRole)
@depends(OpsPingAction, mode=UseCase.extend, description="Cross-domain action dependency (store)")
class DependCrossDomainAction(BaseAction["DependCrossDomainAction.Params", "DependCrossDomainAction.Result"]):
    class Params(BaseParams):
        token: str = Field(default="cross", description="Opaque token")

    class Result(BaseResult):
        peer: str = Field(description="Resolved foreign action name")

    @summary_aspect("Resolve cross-domain peer")
    async def resolve_summary(
        self,
        params: DependCrossDomainAction.Params,
        state: Any,
        box: Any,
        connections: Any,
    ) -> DependCrossDomainAction.Result:
        peer = box.resolve(OpsPingAction)
        assert isinstance(peer, OpsPingAction)
        return DependCrossDomainAction.Result(peer=peer.__class__.__name__)
