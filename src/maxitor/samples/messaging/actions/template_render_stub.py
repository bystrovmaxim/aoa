# src/maxitor/samples/messaging/actions/template_render_stub.py
from __future__ import annotations

from typing import Any

from pydantic import Field

from action_machine.auth import NoneRole
from action_machine.intents.aspects import summary_aspect
from action_machine.intents.check_roles import check_roles
from action_machine.intents.meta import meta
from action_machine.model import BaseAction, BaseParams, BaseResult
from maxitor.samples.messaging.domain import MessagingDomain


@meta(description="Render notification template (messaging sample stub)", domain=MessagingDomain)
@check_roles(NoneRole)
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
        state: Any,
        box: Any,
        connections: Any,
    ) -> TemplateRenderStubAction.Result:
        return TemplateRenderStubAction.Result(body_len=32 + len(params.template_id))
