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


class OpsPingParams(BaseParams):
    ping: str = Field(default="ping", description="Ping payload")


class OpsPingResult(BaseResult):
    message: str = Field(description="Pong message")


@meta(description="Health ping for the storefront slice", domain=StoreDomain)
@check_roles(NoneRole)
class OpsPingAction(BaseAction[OpsPingParams, OpsPingResult]):
    @summary_aspect("Pong")
    async def pong_summary(
        self,
        params: OpsPingParams,
        state: Any,
        box: Any,
        connections: Any,
    ) -> OpsPingResult:
        return OpsPingResult(message="pong")
