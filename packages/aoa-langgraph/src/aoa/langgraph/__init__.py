# packages/aoa-langgraph/src/aoa/langgraph/__init__.py
"""
``aoa-langgraph`` — AOA integration with LangGraph.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provides the public API for running AOA ``BaseAction`` nodes inside a compiled
LangGraph state graph. Two primitives cover the two workflow styles:

``LangGraphAdapter``
    Classic adapter: build topology once, call ``.compile()`` → standard
    LangGraph ``CompiledGraph``.  Suited for standalone LangGraph projects that
    want AOA's role, connection, and context machinery per node.

``LangGraphController``
    AOA-native controller: fluent builder with a typed data contract
    (``.inp()`` / ``.mid()`` / ``.out()``) and topology API.  Suited for
    applications that run everything through ``ActionProductMachine``.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    External apps / tests
             |
             v
      import aoa.langgraph
             |
     +-------+----------+-----------+
     |       |          |           |
  adapter  controller  agent_state  sentinel / exceptions

"""

from aoa.langgraph.adapter import LangGraphAdapter
from aoa.langgraph.agent_state import AgentState
from aoa.langgraph.controller import LangGraphController
from aoa.langgraph.exceptions import (
    ControllerAlreadyBuiltError,
    DuplicateFieldError,
    FieldNotReadyError,
    InconsistentFinishOutputError,
    MissingConnectionError,
    MissingFieldDescriptionError,
    NoOutputFieldsError,
    RouteKeyError,
    StateFieldMismatchError,
    UndeclaredOutputFieldError,
    UnregisteredNodeError,
)
from aoa.langgraph.sentinel import UNSET, UnsetType
from aoa.langgraph.wrapper_langgraph_controller import WrapperLangGraphController

__all__ = [
    "UNSET",
    "AgentState",
    "ControllerAlreadyBuiltError",
    "DuplicateFieldError",
    "FieldNotReadyError",
    "InconsistentFinishOutputError",
    "LangGraphAdapter",
    "LangGraphController",
    "MissingConnectionError",
    "MissingFieldDescriptionError",
    "NoOutputFieldsError",
    "RouteKeyError",
    "StateFieldMismatchError",
    "UndeclaredOutputFieldError",
    "UnregisteredNodeError",
    "UnsetType",
    "WrapperLangGraphController",
]
