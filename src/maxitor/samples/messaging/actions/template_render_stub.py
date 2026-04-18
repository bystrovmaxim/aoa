# src/maxitor/samples/messaging/actions/template_render_stub.py
from __future__ import annotations

from typing import Any

from pydantic import Field

from action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from action_machine.intents.auth.check_roles_decorator import check_roles
from action_machine.intents.auth.none_role import NoneRole
from action_machine.intents.meta.meta_decorator import meta
from action_machine.model.base_action import BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from maxitor.samples.messaging.domain import MessagingDomain


class TemplateRenderStubParams(BaseParams):
    template_id: str = Field(description="Template id")


class TemplateRenderStubResult(BaseResult):
    body_len: int = Field(description="Stub rendered body length", ge=0)


@meta(description="Render notification template (messaging sample stub)", domain=MessagingDomain)
@check_roles(NoneRole)
class TemplateRenderStubAction(BaseAction[TemplateRenderStubParams, TemplateRenderStubResult]):
    @summary_aspect("Render")
    async def render_summary(
        self,
        params: TemplateRenderStubParams,
        state: Any,
        box: Any,
        connections: Any,
    ) -> TemplateRenderStubResult:
        return TemplateRenderStubResult(body_len=32 + len(params.template_id))
