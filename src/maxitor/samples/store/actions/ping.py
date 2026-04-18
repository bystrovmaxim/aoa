# src/maxitor/samples/store/actions/ping.py
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
from maxitor.samples.store.domain import StoreDomain


@meta(description="Health ping for the storefront slice", domain=StoreDomain)
@check_roles(NoneRole)
class OpsPingAction(BaseAction["OpsPingAction.Params", "OpsPingAction.Result"]):
    class Params(BaseParams):
        ping: str = Field(default="ping", description="Ping payload")

    class Result(BaseResult):
        message: str = Field(description="Pong message")

    @summary_aspect("Pong")
    async def pong_summary(
        self,
        params: OpsPingAction.Params,
        state: Any,
        box: Any,
        connections: Any,
    ) -> OpsPingAction.Result:
        return OpsPingAction.Result(message="pong")
