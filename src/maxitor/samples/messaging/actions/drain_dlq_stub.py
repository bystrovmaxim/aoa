# src/maxitor/samples/messaging/actions/drain_dlq_stub.py
from __future__ import annotations

from typing import Any

from pydantic import Field

from action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from action_machine.intents.auth.check_roles_decorator import check_roles
from action_machine.auth.none_role import NoneRole
from action_machine.intents.meta.meta_decorator import meta
from action_machine.model.base_action import BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from maxitor.samples.messaging.domain import MessagingDomain


@meta(description="Drain DLQ stub (messaging sample)", domain=MessagingDomain)
@check_roles(NoneRole)
class DrainDlqStubAction(BaseAction["DrainDlqStubAction.Params", "DrainDlqStubAction.Result"]):
    class Params(BaseParams):
        max_messages: int = Field(default=10, description="Max messages to drain", ge=0, le=1000)

    class Result(BaseResult):
        drained: int = Field(description="Stub drained count", ge=0)

    @summary_aspect("Drain")
    async def drain_summary(
        self,
        params: DrainDlqStubAction.Params,
        state: Any,
        box: Any,
        connections: Any,
    ) -> DrainDlqStubAction.Result:
        return DrainDlqStubAction.Result(drained=min(params.max_messages, 3))
