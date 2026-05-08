# packages/aoa-action-machine/src/aoa/action_machine/model/base_result.py
"""
Immutable action result model.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``BaseResult`` is the base output contract in ActionMachine.
An instance is produced by a summary aspect (or ``@on_error`` handler)
and returned to the caller as the final action outcome.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

A summary aspect creates a regular ``BaseResult`` subclass:

    @summary_aspect("Build result")
    async def build_result_summary(self, params, state, box, connections):
        return OrderResult(
            order_id=f"ORD_{params.user_id}",
            status="created",
            total=state["total"],
        )

``@on_error`` may return an alternative result:

    @on_error(ValueError, description="Validation error")
    async def validation_on_error(self, params, state, box, connections, error):
        return OrderResult(order_id="ERR", status="validation_error", total=0)

Plugins read result via ``event.result`` but cannot mutate it.
Adapters (FastAPI, MCP) serialize it through ``model_dump()``.

═══════════════════════════════════════════════════════════════════════════════
DIFFERENCE FROM BaseParams AND BaseState
═══════════════════════════════════════════════════════════════════════════════

    BaseParams  - frozen, extra="forbid". Input parameters.
    BaseState   - frozen, extra="allow".  Intermediate pipeline state.
    BaseResult  - frozen, extra="forbid". Final action result.

Params comes from outside and stays immutable. State lives inside pipeline flow.
Result is built by the summary aspect and returned to calling code.

"""

from pydantic import ConfigDict

from aoa.action_machine.model.base_schema import BaseSchema
from aoa.graph.exclude_graph_model import exclude_graph_model


@exclude_graph_model
class BaseResult(BaseSchema):
    """Frozen base class for final action result payloads."""

    model_config = ConfigDict(frozen=True, extra="forbid")
