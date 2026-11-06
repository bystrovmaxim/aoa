# packages/aoa-action-machine/src/aoa/action_machine/model/base_params.py
"""
BaseParams — immutable action input parameters.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``BaseParams`` is the base class for action input payloads in ActionMachine.
It defines the typed structure of data passed into the action/aspect pipeline.
Instances are immutable (``frozen=True``), and unknown fields are rejected
(``extra="forbid"``).

═══════════════════════════════════════════════════════════════════════════════
INHERITANCE
═══════════════════════════════════════════════════════════════════════════════

    BaseSchema(BaseModel)
        └── BaseParams (frozen=True, extra="forbid")

═══════════════════════════════════════════════════════════════════════════════
IMMUTABILITY
═══════════════════════════════════════════════════════════════════════════════

Immutable parameters are an architectural choice that provides:

- Predictability: aspects cannot accidentally mutate input.
- Safety: one Params instance can be safely shared across aspects, plugins,
  and error handlers.
- Debuggability: values remain equal to the original request payload.

═══════════════════════════════════════════════════════════════════════════════
STRICT SHAPE (extra="forbid")
═══════════════════════════════════════════════════════════════════════════════

Params contain only explicitly declared fields. Passing unknown fields raises
``ValidationError`` and protects against typos or accidental payload noise.

If additional fields are needed, define them explicitly in a subclass:

    class ExtendedOrderParams(OrderParams):
        priority: int = Field(description="Order priority")

═══════════════════════════════════════════════════════════════════════════════
PYDANTIC CAPABILITIES
═══════════════════════════════════════════════════════════════════════════════

Inheritance from Pydantic ``BaseModel`` (via ``BaseSchema``) provides:

- Type validation at construction time.
- Constraints via ``Field(gt=0, min_length=3, pattern=...)``.
- Schema examples via ``Field(examples=[...])``.
- JSON Schema via ``model_json_schema()`` for OpenAPI and MCP.
- Serialization via ``model_dump()`` for adapters and logging.

═══════════════════════════════════════════════════════════════════════════════
DICT-LIKE ACCESS (inherited from BaseSchema)
═══════════════════════════════════════════════════════════════════════════════

    params["user_id"]                    # -> "user_123"
    "amount" in params                   # -> True
    params.get("currency", "USD")        # -> "USD"
    list(params.keys())                  # -> ["user_id", "amount", "currency"]
    params.resolve("address.city")       # -> "Moscow"
    params.model_dump()                  # -> {"user_id": "user_123", ...}

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    Request payload
         |
         v
    BaseParams subclass (Pydantic validation, frozen/forbid)
         |
         +--> Action/aspect pipeline reads immutable values
         +--> introspection/OpenAPI/MCP reads field descriptions
         |
         v
    model_dump()/model_json_schema() for adapters and tooling

"""

from typing import Any, Self

from pydantic import ConfigDict, model_validator

from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.model.base_schema import BaseSchema
from aoa.action_machine.model.full_entities import refuse_partial_entities
from aoa.action_machine.naming.suffix import require_suffix


@exclude_graph_model
class BaseParams(BaseSchema):
    """
    AI-CORE-BEGIN
    ROLE: Immutable action input contract.
    CONTRACT: Every descendant ends with ``Params``; invalid declarations raise NamingSuffixError.
    INVARIANTS: Frozen fields, forbidden extras and full entity values remain enforced.
    AI-CORE-END
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Require the ``Params`` suffix for every descendant."""
        super().__init_subclass__(**kwargs)
        require_suffix(cls, "BaseParams", "Params")

    @model_validator(mode="after")
    def _carry_full_entities(self) -> Self:
        """A field typed by an entity carries a full one; a projection is the field for a part (#408)."""
        refuse_partial_entities(self)
        return self
