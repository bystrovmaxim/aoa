# src/maxitor/samples/support/actions/depend_cross_domain.py
"""Сценарий: ``@depends`` на ``BaseAction`` в другом домене."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from action_machine.auth import NoneRole
from action_machine.intents.aspects import summary_aspect
from action_machine.intents.check_roles import check_roles
from action_machine.intents.depends import depends
from action_machine.intents.meta import meta
from action_machine.model import BaseAction, BaseParams, BaseResult
from maxitor.samples.store.actions.ping import OpsPingAction
from maxitor.samples.support.domain import SupportDomain


@meta(
    description="Resolves an action from StoreDomain via @depends (graph: cross-domain)",
    domain=SupportDomain,
)
@check_roles(NoneRole)
@depends(OpsPingAction, description="Cross-domain action dependency (store)")
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
