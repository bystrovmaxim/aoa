# packages/aoa-action-machine/src/aoa/action_machine/model/base_result.py
"""
BaseResult — immutable action result model.

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

from typing import Any, Self

from pydantic import ConfigDict, model_validator

from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.model.base_schema import BaseSchema
from aoa.action_machine.model.full_entities import refuse_partial_entities
from aoa.action_machine.naming.suffix import require_suffix


@exclude_graph_model
class BaseResult(BaseSchema):
    """
    AI-CORE-BEGIN
    ROLE: Immutable action output contract.
    CONTRACT: Every descendant ends with ``Result``; invalid declarations raise NamingSuffixError.
    INVARIANTS: Frozen fields, forbidden extras and full entity values remain enforced.
    AI-CORE-END
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Require the ``Result`` suffix for every descendant."""
        super().__init_subclass__(**kwargs)
        require_suffix(cls, "BaseResult", "Result")

    @model_validator(mode="after")
    def _carry_full_entities(self) -> Self:
        """A field typed by an entity carries a full one; a projection is the field for a part (#408)."""
        refuse_partial_entities(self)
        return self
