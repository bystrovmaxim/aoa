# packages/aoa-demo/src/aoa/demo/model/messaging/actions/template_render_stub.py
from __future__ import annotations

from pydantic import Field

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult, BaseState
from aoa.action_machine.resources import BaseResource
from aoa.action_machine.runtime.tools_box import ToolsBox
from aoa.demo.model.messaging.domain import MessagingDomain


@meta(description="Render notification template (messaging sample stub)", domain=MessagingDomain)
@check_roles(GuestRole)
class TemplateRenderStubAction(
    BaseAction["TemplateRenderStubAction.Params", "TemplateRenderStubAction.Result"],
):
    class Params(BaseParams):
        template_id: str = Field(description="Template id")

    class Result(BaseResult):
        body_len: int = Field(description="Stub rendered body length", ge=0)

    @summary_aspect("Render")
    async def render_summary(
        self,
        params: TemplateRenderStubAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> TemplateRenderStubAction.Result:
        return TemplateRenderStubAction.Result(body_len=32 + len(params.template_id))
