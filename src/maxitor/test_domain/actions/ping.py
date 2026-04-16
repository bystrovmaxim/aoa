# src/maxitor/test_domain/actions/ping.py
"""Минимальное действие: NoneRole + summary."""

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
from maxitor.test_domain.domain import TestDomain


class TestPingParams(BaseParams):
    ping: str = Field(default="ping", description="Ping payload")


class TestPingResult(BaseResult):
    message: str = Field(description="Pong message")


@meta(description="Synthetic ping", domain=TestDomain)
@check_roles(NoneRole)
class TestPingAction(BaseAction[TestPingParams, TestPingResult]):
    @summary_aspect("Pong")
    async def pong_summary(
        self,
        params: TestPingParams,
        state: Any,
        box: Any,
        connections: Any,
    ) -> TestPingResult:
        return TestPingResult(message="pong")
