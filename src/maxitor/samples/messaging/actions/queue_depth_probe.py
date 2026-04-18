# src/maxitor/samples/messaging/actions/queue_depth_probe.py
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


class QueueDepthProbeParams(BaseParams):
    queue_name: str = Field(description="Logical queue name")


class QueueDepthProbeResult(BaseResult):
    depth: int = Field(description="Stub depth", ge=0)


@meta(description="Probe queue depth (messaging sample stub)", domain=MessagingDomain)
@check_roles(NoneRole)
class QueueDepthProbeAction(BaseAction[QueueDepthProbeParams, QueueDepthProbeResult]):
    @summary_aspect("Probe")
    async def probe_summary(
        self,
        params: QueueDepthProbeParams,
        state: Any,
        box: Any,
        connections: Any,
    ) -> QueueDepthProbeResult:
        return QueueDepthProbeResult(depth=len(params.queue_name) % 5)
