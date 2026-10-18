# packages/aoa-demo/src/aoa/demo/model/support/actions/depend_same_domain_action.py
"""DependSameDomainAction — resolves Support ping via ``@depends``."""

from __future__ import annotations

from pydantic import Field

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.depends import UseCase, depends
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.runtime.tools_box import ToolsBox
from aoa.demo.model.support.actions.support_ping import SupportPingAction
from aoa.demo.model.support.support_domain import SupportDomain


@meta(
    description="Resolves another action in SupportDomain via @depends (graph: same-domain)",
    domain=SupportDomain,
)
@check_roles(GuestRole)
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
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> DependSameDomainAction.Result:
        peer = await box.resolve(SupportPingAction)
        assert isinstance(peer, SupportPingAction)
        return DependSameDomainAction.Result(peer=peer.__class__.__name__)
