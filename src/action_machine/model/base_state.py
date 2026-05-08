# src/action_machine/model/base_state.py
"""
Frozen aspect-pipeline state with dynamic fields.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``BaseState`` is an immutable container for accumulated values between aspect
pipeline steps. Each regular aspect returns a plain ``dict`` with new fields.
The machine validates that dict with checkers and creates a NEW ``BaseState``
by merging previous data with returned fields. Aspects receive state as
read-only input; mutation is impossible after construction.

═══════════════════════════════════════════════════════════════════════════════
INHERITANCE
═══════════════════════════════════════════════════════════════════════════════

    BaseSchema(BaseModel)
        └── BaseState (frozen=True, extra="allow")

═══════════════════════════════════════════════════════════════════════════════
FROZEN SEMANTICS
═══════════════════════════════════════════════════════════════════════════════

``BaseState`` is fully immutable after creation (``frozen=True``):

    state = BaseState(total=1500, user="agent")
    state.total = 0           # -> ValidationError
    state["total"] = 0        # -> TypeError (no __setitem__)

The only way to "change" state is to create a new instance:

    new_state = BaseState(**{**old_state.to_dict(), "discount": 10})

This ensures aspects cannot write into state directly and bypass checkers.
The machine controls every added field through validation of aspect output.

═══════════════════════════════════════════════════════════════════════════════
DYNAMIC FIELDS (extra="allow")
═══════════════════════════════════════════════════════════════════════════════

Unlike ``BaseParams`` and ``BaseResult``, ``BaseState`` has no predefined field
set. Fields are defined by dicts returned from aspects and may be dynamic.
With ``extra="allow"``, Pydantic accepts arbitrary keys passed via kwargs.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    1. Machine creates empty state: state = BaseState()
    2. For each regular aspect:
       a. Call aspect with current frozen state.
       b. Aspect returns dict with new fields.
       c. Machine validates returned dict with checkers.
       d. Machine creates new state: BaseState(**{**state.to_dict(), **new_dict})
    3. Summary aspect receives final frozen state and builds Result.

At each step, state is a new object. Previous state is never modified.

═══════════════════════════════════════════════════════════════════════════════
SERIALIZATION
═══════════════════════════════════════════════════════════════════════════════

``to_dict()`` returns all fields via ``model_dump()``.
It is used by the machine for merge operations, and for passing state to
plugins (``PluginEvent.state_aspect``) and loggers.

═══════════════════════════════════════════════════════════════════════════════
DIFFERENCE FROM BaseParams AND BaseResult
═══════════════════════════════════════════════════════════════════════════════

    BaseParams  - frozen, extra="forbid". Input parameters. Strict shape.
    BaseState   - frozen, extra="allow".  Intermediate state. Dynamic fields.
    BaseResult  - frozen, extra="forbid". Final result. Strict shape.

"""

from pydantic import ConfigDict

from action_machine.model.base_schema import BaseSchema


class BaseState(BaseSchema):
    """
    Frozen pipeline state with dynamic fields.

    Created by the machine from dict payloads returned by aspects. Supports
    arbitrary keys at creation (``extra="allow"``) and forbids any mutation
    afterwards (``frozen=True``).
    """

    model_config = ConfigDict(frozen=True, extra="allow")

    def to_dict(self) -> dict[str, object]:
        """
        Return a dictionary view of all state fields.

        Used by runtime to merge state with aspect output and to pass payloads
        to plugins/loggers.
        """
        return self.model_dump()

    def __repr__(self) -> str:
        """
        Return a human-readable debug representation.

        Format: ``BaseState(key1=value1, key2=value2, ...)``.
        """
        fields = self.to_dict()
        pairs = ", ".join(f"{k}={v!r}" for k, v in fields.items())
        return f"{type(self).__name__}({pairs})"
