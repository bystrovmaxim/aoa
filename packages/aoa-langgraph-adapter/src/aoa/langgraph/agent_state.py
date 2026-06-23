"""AgentState — base class for LangGraph agentstate schemas."""

from __future__ import annotations

from pydantic import ConfigDict

from aoa.action_machine.model.base_schema import BaseSchema


class AgentState(BaseSchema):
    """Base class for LangGraph agentstate schemas.

    Inherit to define the state schema for a LangGraph graph:

        class TicketState(AgentState):
            ticket_id: str
            category: str = ""
            resolved: bool = False

    Provides dict-like field access (``state["field"]``) via BaseSchema.__getitem__,
    so node functions can read state fields by string key without extra conversion.

    Not frozen — LangGraph creates a new instance from the merged dict after each
    node, so mutability of the instance is not relevant.
    """

    model_config = ConfigDict(frozen=False, extra="ignore")
