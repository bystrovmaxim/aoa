# src/maxitor/samples/support/actions/depend_on_actions.py
"""Два сценария: ``@depends`` на ``BaseAction`` в том же домене и в другом."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from action_machine.dependencies.depends_decorator import depends
from action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from action_machine.intents.auth.check_roles_decorator import check_roles
from action_machine.intents.auth.none_role import NoneRole
from action_machine.intents.meta.meta_decorator import meta
from action_machine.model.base_action import BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from maxitor.samples.store.actions.ping import OpsPingAction
from maxitor.samples.support.actions.support_ping import SupportPingAction
from maxitor.samples.support.domain import SupportDomain


class DependSameDomainParams(BaseParams):
    token: str = Field(default="same", description="Opaque token")


class DependSameDomainResult(BaseResult):
    peer: str = Field(description="Resolved peer action name")


@meta(
    description="Resolves another action in SupportDomain via @depends (graph: same-domain)",
    domain=SupportDomain,
)
@check_roles(NoneRole)
@depends(SupportPingAction, description="Same-domain action dependency")
class DependSameDomainAction(BaseAction[DependSameDomainParams, DependSameDomainResult]):
    @summary_aspect("Resolve same-domain peer")
    async def resolve_summary(
        self,
        params: DependSameDomainParams,
        state: Any,
        box: Any,
        connections: Any,
    ) -> DependSameDomainResult:
        peer = box.resolve(SupportPingAction)
        assert isinstance(peer, SupportPingAction)
        return DependSameDomainResult(peer=peer.__class__.__name__)


class DependCrossDomainParams(BaseParams):
    token: str = Field(default="cross", description="Opaque token")


class DependCrossDomainResult(BaseResult):
    peer: str = Field(description="Resolved foreign action name")


@meta(
    description="Resolves an action from StoreDomain via @depends (graph: cross-domain)",
    domain=SupportDomain,
)
@check_roles(NoneRole)
@depends(OpsPingAction, description="Cross-domain action dependency (store)")
class DependCrossDomainAction(BaseAction[DependCrossDomainParams, DependCrossDomainResult]):
    @summary_aspect("Resolve cross-domain peer")
    async def resolve_summary(
        self,
        params: DependCrossDomainParams,
        state: Any,
        box: Any,
        connections: Any,
    ) -> DependCrossDomainResult:
        peer = box.resolve(OpsPingAction)
        assert isinstance(peer, OpsPingAction)
        return DependCrossDomainResult(peer=peer.__class__.__name__)
