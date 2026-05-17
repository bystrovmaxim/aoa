# packages/aoa-examples/src/aoa/examples/model/support/actions/depend_cross_domain.py
"""Scenario: ``@depends`` on a ``BaseAction`` in another domain."""

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
from aoa.examples.model.support.domain import SupportDomain


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


@meta(
    description="Runs store OpsPingAction via box.run with UseCase.include (cross-domain + contract)",
    domain=SupportDomain,
)
@check_roles(NoneRole)
@depends(
    OpsPingAction,
    mode=UseCase.include,
    description="Cross-domain include — store peer must execute via _run_internal",
)
class DependCrossDomainIncludeAction(
    BaseAction["DependCrossDomainIncludeAction.Params", "DependCrossDomainIncludeAction.Result"],
):
    class Params(BaseParams):
        token: str = Field(default="cross-inc", description="Opaque token")

    class Result(BaseResult):
        peer: str = Field(description="Peer action name after boxed run")
        pong: str = Field(description="Message from nested OpsPing result")

    @summary_aspect("Run cross-domain store peer (include)")
    async def run_store_include_peer_summary(
        self,
        params: DependCrossDomainIncludeAction.Params,
        state: Any,
        box: Any,
        connections: Any,
    ) -> DependCrossDomainIncludeAction.Result:
        nested = await box.run(OpsPingAction, OpsPingAction.Params())
        return DependCrossDomainIncludeAction.Result(
            peer=OpsPingAction.__name__,
            pong=nested.message,
        )
