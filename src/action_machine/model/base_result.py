# src/action_machine/model/base_result.py
"""
Immutable action result model.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``BaseResult`` is the base output contract in ActionMachine.
An instance is produced by a summary aspect (or ``@on_error`` handler)
and returned to the caller as the final action outcome.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- ``frozen=True``: field writes after construction are forbidden.
- ``extra="forbid"``: result contains only explicitly declared fields.

    result = OrderResult(order_id="ORD-1", status="created", total=1500.0)
    result.status = "paid"        # -> ValidationError

The only way to "change" a result is to create a new instance:

    updated = result.model_copy(update={"status": "paid"})

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

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    from pydantic import Field
    from action_machine.model.base_result import BaseResult

    class OrderResult(BaseResult):
        order_id: str = Field(description="Created order identifier")
        status: str = Field(description="Order status", examples=["created"])
        total: float = Field(description="Final amount", ge=0)

    result = OrderResult(order_id="ORD-123", status="created", total=1500.0)

    # Reads via dict-like API (inherited from BaseSchema):
    result["status"]            # -> "created"
    result.resolve("total")     # -> 1500.0
    result.keys()               # -> ["order_id", "status", "total"]

    # Serialization:
    result.model_dump()         # -> {"order_id": "ORD-123", "status": "created", "total": 1500.0}

    # Writes are forbidden (frozen):
    result.status = "paid"      # -> ValidationError

    # Unknown fields are forbidden (extra="forbid"):
    OrderResult(order_id="x", status="y", total=0, unknown="z")  # -> ValidationError

    # "Change" by creating a new instance:
    updated = result.model_copy(update={"status": "paid"})

    # JSON Schema for FastAPI and MCP:
    OrderResult.model_json_schema()
    # {"properties": {"order_id": {"description": "Created order identifier", ...}, ...}}

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Mutating fields after construction is rejected by frozen model config.
- Unknown fields are rejected due to ``extra="forbid"``.
- This class defines framework-level output contract only; domain semantics
  belong to concrete result subclasses.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Immutable final output contract for action execution.
CONTRACT: Result models are typed, frozen, and strictly shaped.
INVARIANTS: frozen=True; extra="forbid"; field descriptions are expected.
FLOW: summary/on_error creates result -> runtime emits -> adapters serialize.
FAILURES: ValidationError on invalid input, unknown fields, or mutation attempt.
EXTENSION POINTS: Extend through dedicated result subclasses per action.
AI-CORE-END
"""

from pydantic import ConfigDict

from action_machine.legacy.described_fields.marker import DescribedFieldsIntent
from action_machine.model.base_schema import BaseSchema


class BaseResult(BaseSchema, DescribedFieldsIntent):
    """
    Frozen base class for final action result payloads.

    Subclasses define concrete output fields with ``Field(..., description=...)``.
    Inherits dict-like and dot-path access from ``BaseSchema`` and described
    field validation contract from ``DescribedFieldsIntent``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")
