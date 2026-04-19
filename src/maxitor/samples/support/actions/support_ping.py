# src/maxitor/samples/support/actions/support_ping.py
"""Базовое действие в домене support — цель для ``@depends`` внутри того же домена."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from action_machine.auth.none_role import NoneRole
from action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from action_machine.intents.check_roles.check_roles_decorator import check_roles
from action_machine.intents.meta.meta_decorator import meta
from action_machine.model.base_action import BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from maxitor.samples.support.domain import SupportDomain


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
