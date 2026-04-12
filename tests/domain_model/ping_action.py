# tests/domain_model/ping_action.py
"""
PingAction — minimal Action for smoke tests.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Simplest Action in the test domain: no parameters, no dependencies or
connections, only a summary aspect returning a fixed "pong" message.

Available to everyone (NoneRole), including anonymous users.
Belongs to SystemDomain.

═══════════════════════════════════════════════════════════════════════════════
USAGE IN TESTS
═══════════════════════════════════════════════════════════════════════════════

- Smoke tests: machine runs, coordinator builds metadata, pipeline executes.
- NoneRole tests: anonymous user without roles passes.
- TestBench: minimal run without mocks or connections.

    result = await bench.run(PingAction(), PingAction.Params(), rollup=False)
    assert result.message == "pong"
"""

from pydantic import Field

from action_machine.aspects.summary_aspect_decorator import summary_aspect
from action_machine.auth import NoneRole, check_roles
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.core.base_state import BaseState
from action_machine.core.meta_decorator import meta
from action_machine.core.tools_box import ToolsBox
from action_machine.resource_managers.base_resource_manager import BaseResourceManager

from .domains import SystemDomain


@meta(description="Service health check", domain=SystemDomain)
@check_roles(NoneRole)
class PingAction(BaseAction["PingAction.Params", "PingAction.Result"]):
    """
    Minimal Action without parameters or dependencies.

    Summary-only aspect returning a fixed "pong" result. NoneRole.
    """

    class Params(BaseParams):
        """PingAction parameters — empty; no input required."""
        pass

    class Result(BaseResult):
        """PingAction result — pong message."""
        message: str = Field(description="Service response message")

    @summary_aspect("Build pong response")
    async def pong_summary(
        self,
        params: "PingAction.Params",
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> "PingAction.Result":
        """Return a fixed Result with message 'pong'."""
        return PingAction.Result(message="pong")
