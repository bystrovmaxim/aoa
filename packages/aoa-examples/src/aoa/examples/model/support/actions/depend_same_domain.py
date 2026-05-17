# packages/aoa-examples/src/aoa/examples/model/support/actions/depend_same_domain.py
"""Scenario: ``@depends`` on a ``BaseAction`` in the same domain."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from aoa.action_machine.auth import NoneRole
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.depends import UseCase, depends
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.examples.model.support.actions.support_ping import SupportPingAction
from aoa.examples.model.support.domain import SupportDomain


@meta(
    description="Resolves another action in SupportDomain via @depends (graph: same-domain)",
    domain=SupportDomain,
)
@check_roles(NoneRole)
@depends(SupportPingAction, mode=UseCase.extend, description="Same-domain action dependency")
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


@meta(
    description="Runs same-domain peer via box.run with UseCase.include (graph + runtime contract)",
    domain=SupportDomain,
)
@check_roles(NoneRole)
@depends(
    SupportPingAction,
    mode=UseCase.include,
    description="Same-domain include — peer must execute via _run_internal",
)
class DependSameDomainIncludeAction(
    BaseAction["DependSameDomainIncludeAction.Params", "DependSameDomainIncludeAction.Result"],
):
    class Params(BaseParams):
        token: str = Field(default="same-inc", description="Opaque token")

    class Result(BaseResult):
        peer: str = Field(description="Peer action name after boxed run")
        peer_ok: bool = Field(description="Ack flag from nested SupportPing result")

    @summary_aspect("Run same-domain peer (include)")
    async def run_include_peer_summary(
        self,
        params: DependSameDomainIncludeAction.Params,
        state: Any,
        box: Any,
        connections: Any,
    ) -> DependSameDomainIncludeAction.Result:
        nested = await box.run(SupportPingAction, SupportPingAction.Params())
        return DependSameDomainIncludeAction.Result(
            peer=SupportPingAction.__name__,
            peer_ok=nested.ok,
        )
