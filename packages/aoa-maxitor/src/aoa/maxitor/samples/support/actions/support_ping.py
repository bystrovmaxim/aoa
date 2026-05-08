# packages/aoa-maxitor/src/aoa/maxitor/samples/support/actions/support_ping.py
"""Baseline support action — target for same-domain ``@depends``."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from aoa.action_machine.auth import NoneRole
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.maxitor.samples.support.domain import SupportDomain


@meta(description="Support slice ping (dependency target for same-domain @depends)", domain=SupportDomain)
@check_roles(NoneRole)
class SupportPingAction(BaseAction["SupportPingAction.Params", "SupportPingAction.Result"]):
    class Params(BaseParams):
        label: str = Field(default="support", description="Probe label")

    class Result(BaseResult):
        ok: bool = Field(description="Stub ok flag")

    @summary_aspect("Ack")
    async def ack_summary(
        self,
        params: SupportPingAction.Params,
        state: Any,
        box: Any,
        connections: Any,
    ) -> SupportPingAction.Result:
        return SupportPingAction.Result(ok=True)
