# tests/action_machine/scenarios/domain_model/depends_mode_host_action.py
"""Host action for PR-3/PR-5 ``@depends`` ``mode`` interchange + wiring tests."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from aoa.action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from aoa.action_machine.intents.check_roles import NoneRole, check_roles
from aoa.action_machine.intents.depends import UseCase, depends
from aoa.action_machine.intents.meta.meta_decorator import meta
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.base_result import BaseResult
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.resources.base_resource import BaseResource

from .domains import SystemDomain
from .ping_action import PingAction
from .services import PaymentServiceResource


@meta(description="host for depends mode graph tests", domain=SystemDomain)
@check_roles(NoneRole)
@depends(PingAction, mode=UseCase.include, description="peer action")
@depends(PaymentServiceResource, description="pay")
class DependsModeHostAction(BaseAction["DependsModeHostAction.Params", "DependsModeHostAction.Result"]):
    class Params(BaseParams):
        pass

    class Result(BaseResult):
        ok: str = Field(default="yes", description="flag")

    @summary_aspect("s")
    async def s_summary(
        self,
        params: DependsModeHostAction.Params,
        state: BaseState,
        box: Any,
        connections: dict[str, BaseResource],
    ) -> DependsModeHostAction.Result:
        return DependsModeHostAction.Result()
