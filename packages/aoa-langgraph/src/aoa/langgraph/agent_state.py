# packages/aoa-langgraph/src/aoa/langgraph/agent_state.py
"""
AgentState — base schema for LangGraph state graphs using LangGraphController.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Base class for user-defined LangGraph state schemas. Provides dict-like field
access via ``state["field"]`` so node functions can read state fields by string
key without extra conversion.

Mid-fields declared with ``.mid()`` start as ``UNSET``. Reading an ``UNSET``
field via ``__getitem__`` raises ``FieldNotReadyError`` — the node-facing guard.
LangGraph itself reconstructs state via ``schema(**input)`` and never calls
``__getitem__``, so ``UNSET`` travels safely across framework hops.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    class TicketState(AgentState):
        ticket_id: str
        category: str = ""
        resolved: bool = False

    state["ticket_id"]  →  str value (inp field, always set)
    state["category"]   →  FieldNotReadyError if UNSET (mid field, not yet produced)
    state["category"]   →  str value after the producing node ran

"""

from __future__ import annotations

from pydantic import ConfigDict

from aoa.action_machine.model.base_schema import BaseSchema
from aoa.langgraph.exceptions import FieldNotReadyError
from aoa.langgraph.sentinel import UnsetType


class AgentState(BaseSchema):
    """
    AI-CORE-BEGIN
        ROLE: Typed state container passed between LangGraph nodes.
        CONTRACT: dict-like read via __getitem__; raises FieldNotReadyError on UNSET mid-fields.
        INVARIANTS: Not frozen — LangGraph rebuilds the instance via schema(**input) each hop.
    AI-CORE-END
    """

    model_config = ConfigDict(frozen=False, extra="ignore", arbitrary_types_allowed=True)

    def __getitem__(self, key: str) -> object:
        """Return field value; raise FieldNotReadyError if the field is still UNSET."""
        value = super().__getitem__(key)
        if isinstance(value, UnsetType):
            raise FieldNotReadyError(key)
        return value
