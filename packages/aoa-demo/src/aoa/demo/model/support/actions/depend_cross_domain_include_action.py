# packages/aoa-demo/src/aoa/demo/model/support/actions/depend_cross_domain_include_action.py
"""DependCrossDomainIncludeAction — ``box.run`` store peer via include."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.depends import UseCase, depends
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.demo.model.store.actions.ping import OpsPingAction
from aoa.demo.model.support.support_domain import SupportDomain


@meta(
    description="Runs store OpsPingAction via box.run with UseCase.include (cross-domain + contract)",
    domain=SupportDomain,
)
@check_roles(GuestRole)
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
