# src/maxitor/samples/support/actions/depend_same_domain.py
"""Сценарий: ``@depends`` на ``BaseAction`` в том же домене."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from action_machine.dependencies.depends_decorator import depends
from action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from action_machine.intents.auth.check_roles_decorator import check_roles
from action_machine.auth.none_role import NoneRole
from action_machine.intents.meta.meta_decorator import meta
from action_machine.model.base_action import BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from maxitor.samples.support.actions.support_ping import SupportPingAction
from maxitor.samples.support.domain import SupportDomain


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
