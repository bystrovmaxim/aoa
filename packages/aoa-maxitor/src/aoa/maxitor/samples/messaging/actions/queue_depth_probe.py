# packages/aoa-maxitor/src/aoa/maxitor/samples/messaging/actions/queue_depth_probe.py
from __future__ import annotations

from typing import Any

from pydantic import Field

from aoa.action_machine.auth import NoneRole
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.maxitor.samples.messaging.domain import MessagingDomain


@meta(description="Probe queue depth (messaging sample stub)", domain=MessagingDomain)
@check_roles(NoneRole)
class QueueDepthProbeAction(BaseAction["QueueDepthProbeAction.Params", "QueueDepthProbeAction.Result"]):
    class Params(BaseParams):
        queue_name: str = Field(description="Logical queue name")

    class Result(BaseResult):
        depth: int = Field(description="Stub depth", ge=0)

    @summary_aspect("Probe")
    async def probe_summary(
        self,
        params: QueueDepthProbeAction.Params,
        state: Any,
        box: Any,
        connections: Any,
    ) -> QueueDepthProbeAction.Result:
        return QueueDepthProbeAction.Result(depth=len(params.queue_name) % 5)
