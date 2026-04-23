# src/action_machine/model/__init__.py
"""
ActionMachine core model public API.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

This package exports the base model contracts used by actions:
``BaseAction``, ``BaseParams``, ``BaseResult``, ``BaseSchema``, ``BaseState``.
Framework exceptions live in :mod:`action_machine.exceptions`.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    Action implementation
          |
          +--> BaseParams  (input contract)
          +--> BaseState   (mutable execution state)
          +--> BaseResult  (output contract)
          +--> BaseSchema  (typed schema helpers)
          |
          v
       BaseAction (ties contracts together)
          |
          v
    Runtime / adapters consume typed model interfaces

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path:
    A feature imports ``BaseAction`` and base contracts from this package and
    defines strongly typed params/state/result models for one action.

Edge case:
    A model validation or contract misuse raises an exception from
    :mod:`action_machine.exceptions`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from action_machine.model.base_action import BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from action_machine.model.base_schema import BaseSchema
from action_machine.model.base_state import BaseState
from action_machine.model.graph_model.checker_graph_node import CheckerGraphNode
from action_machine.model.graph_model.compensator_graph_node import CompensatorGraphNode
from action_machine.model.graph_model.error_handler_graph_node import ErrorHandlerGraphNode
from action_machine.model.graph_model.params_graph_node import ParamsGraphNode
from action_machine.model.graph_model.params_graph_node_inspector import (
    ParamsGraphNodeInspector,
)
from action_machine.model.graph_model.regular_aspect_graph_node import RegularAspectGraphNode
from action_machine.model.graph_model.result_graph_node import ResultGraphNode
from action_machine.model.graph_model.result_graph_node_inspector import (
    ResultGraphNodeInspector,
)
from action_machine.model.graph_model.summary_aspect_graph_node import SummaryAspectGraphNode

if TYPE_CHECKING:
    from action_machine.model.graph_model.action_graph_node import ActionGraphNode
    from action_machine.model.graph_model.action_graph_node_inspector import (
        ActionGraphNodeInspector,
    )


def __getattr__(name: str) -> Any:
    """Lazy exports — avoid import cycles with :mod:`action_machine.domain.base_domain` / graph."""
    if name == "ActionGraphNode":
        from action_machine.model.graph_model.action_graph_node import (  # pylint: disable=import-outside-toplevel
            ActionGraphNode as ActionGraphNodeImpl,
        )

        return ActionGraphNodeImpl
    if name == "ActionGraphNodeInspector":
        from action_machine.model.graph_model.action_graph_node_inspector import (  # pylint: disable=import-outside-toplevel
            ActionGraphNodeInspector as ActionGraphNodeInspectorImpl,
        )

        return ActionGraphNodeInspectorImpl
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "ActionGraphNode",
    "ActionGraphNodeInspector",
    "BaseAction",
    "BaseParams",
    "BaseResult",
    "BaseSchema",
    "BaseState",
    "CheckerGraphNode",
    "CompensatorGraphNode",
    "ErrorHandlerGraphNode",
    "ParamsGraphNode",
    "ParamsGraphNodeInspector",
    "RegularAspectGraphNode",
    "ResultGraphNode",
    "ResultGraphNodeInspector",
    "SummaryAspectGraphNode",
]
