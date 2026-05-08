# packages/aoa-maxitor/src/aoa/maxitor/samples/support/actions/depend_same_domain.py
"""Scenario: ``@depends`` on a ``BaseAction`` in the same domain."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from aoa.action_machine.auth import NoneRole
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.depends import depends
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.maxitor.samples.support.actions.support_ping import SupportPingAction
from aoa.maxitor.samples.support.domain import SupportDomain


@meta(
    description="Resolves another action in SupportDomain via @depends (graph: same-domain)",
    domain=SupportDomain,
)
@check_roles(NoneRole)
@depends(SupportPingAction, description="Same-domain action dependency")
class DependSameDomainAction(BaseAction["DependSameDomainAction.Params", "DependSameDomainAction.Result"]):
    class Params(BaseParams):
        token: str = Field(default="same", description="Opaque token")

    class Result(BaseResult):
        peer: str = Field(description="Resolved peer action name")

    @summary_aspect("Resolve same-domain peer")
    async def resolve_summary(
        self,
        params: DependSameDomainAction.Params,
        state: Any,
        box: Any,
        connections: Any,
    ) -> DependSameDomainAction.Result:
        peer = box.resolve(SupportPingAction)
        assert isinstance(peer, SupportPingAction)
        return DependSameDomainAction.Result(peer=peer.__class__.__name__)
