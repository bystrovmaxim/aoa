# src/action_machine/model/base_params.py
"""
Immutable action input parameters.

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
FIELD DESCRIPTIONS
═══════════════════════════════════════════════════════════════════════════════

Each field should use ``Field(description="...")``. Description completeness is
validated by ``validate_described_schema`` /
``validate_described_schemas_for_action`` (see described-fields intent).
Descriptions are used for OpenAPI (FastAPI), JSON Schema (MCP), and introspection.

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
         +--> Introspection/OpenAPI/MCP reads field descriptions
         |
         v
    model_dump()/model_json_schema() for adapters and tooling

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    from pydantic import Field
    from action_machine.model.base_params import BaseParams

    class OrderParams(BaseParams):
        user_id: str = Field(description="User identifier", examples=["user_123"])
        amount: float = Field(description="Order amount", gt=0)
        currency: str = Field(default="USD", description="ISO 4217 currency code")

    params = OrderParams(user_id="user_123", amount=1500.0)

    params["user_id"]           # -> "user_123"
    params.resolve("currency")  # -> "USD"
    params.keys()               # -> ["user_id", "amount", "currency"]

    # Writes are forbidden (frozen):
    params.amount = 0           # -> ValidationError

    # Unknown fields are forbidden (extra="forbid"):
    OrderParams(user_id="x", amount=1, unknown="y")  # -> ValidationError

    # JSON Schema for FastAPI and MCP:
    OrderParams.model_json_schema()
    # {"properties": {"user_id": {"description": "User identifier", ...}, ...}}

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Immutable input contract for action execution.
CONTRACT: Subclasses declare typed fields; runtime treats params as read-only.
INVARIANTS: frozen=True; extra="forbid"; schema descriptions expected.
FLOW: validate payload -> pass through pipeline -> serialize/introspect.
FAILURES: ValidationError on unknown/invalid fields or forbidden assignment.
EXTENSION POINTS: Extend via subclasses with explicit typed field definitions.
AI-CORE-END
"""

from pydantic import ConfigDict

from action_machine.legacy.described_fields.marker import DescribedFieldsIntent
from action_machine.model.base_schema import BaseSchema


class BaseParams(BaseSchema, DescribedFieldsIntent):
    """
    Immutable action parameters (frozen + forbid).

    Inherits dict-like and dot-path access from ``BaseSchema`` plus described
    field validation contract from ``DescribedFieldsIntent``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")
