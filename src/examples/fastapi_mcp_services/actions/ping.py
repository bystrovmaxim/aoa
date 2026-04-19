# src/examples/fastapi_mcp_services/actions/ping.py
"""
PingAction — service liveness check.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Minimal unauthenticated action. Returns ``{"message": "pong"}``. Suitable for
health checks, monitoring, and post-deploy smoke tests.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    GET /api/v1/ping
      |
      v
  Params (empty)
      |
      v
  pong_summary -> Result(message="pong")

Nested ``Params`` and ``Result`` are defined inside the action class. Action
description comes from ``@meta(description=...)``; aspect description from
``@summary_aspect("...")``.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- ``NoneRole`` / ``@check_roles(NoneRole)``: callable without authentication.
- ``Params`` has no fields (empty ``BaseParams``).
- Generic arguments use string forward refs (``"PingAction.Params"``) because
  nested classes are not defined yet at class body parse time; runtime resolves
  them via ``extract_action_types`` (module + class namespace).

Nested-model benefits (same pattern as other example actions):

- **Locality** — input/output types sit next to the logic that uses them.
- **Namespaces** — ``PingAction.Params`` and ``CreateOrderAction.Params`` do not clash.
- **Self-documentation** — one class shows inputs, outputs, and pipeline.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    GET /api/v1/ping  ->  {"message": "pong"}

    Edge case: no request body is required; empty params model is valid.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Example only; production health endpoints may add dependencies or stricter contracts.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Minimal shared ping action for FastAPI/MCP example services.
CONTRACT: No auth; summary-only; fixed ``pong`` response shape.
INVARIANTS: Empty params; single summary aspect; ``SystemDomain`` metadata.
═══════════════════════════════════════════════════════════════════════════════
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from pydantic import Field

from action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from action_machine.intents.check_roles import NoneRole, check_roles
from action_machine.intents.meta.meta_decorator import meta
from action_machine.model.base_action import BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from action_machine.model.base_state import BaseState
from action_machine.resources.base_resource_manager import BaseResourceManager
from action_machine.runtime.tools_box import ToolsBox

from ..domains import SystemDomain


@meta(description="Service liveness check", domain=SystemDomain)
@check_roles(NoneRole)
class PingAction(BaseAction["PingAction.Params", "PingAction.Result"]):

    class Params(BaseParams):
        """Ping request parameters — empty; no input required."""
        pass

    class Result(BaseResult):
        """Ping response payload."""
        message: str = Field(description="Response message", examples=["pong"])

    @summary_aspect("Build pong response")
    async def pong_summary(
        self,
        params: "PingAction.Params",
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> "PingAction.Result":
        """Return fixed ``pong`` message."""
        return PingAction.Result(message="pong")
