# src/action_machine/model/__init__.py
"""
ActionMachine core model public API.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

This package exports the base model contracts used by actions:
``BaseAction``, ``BaseParams``, ``BaseResult``, ``ParamsStub``, ``ResultStub``,
``BaseSchema``, ``BaseState``.
Framework exceptions live in :mod:`action_machine.exceptions`.

Graph interchange vertex types (:class:`~action_machine.graph_model.nodes.action_graph_node.ActionGraphNode`,
etc.) are re-exported lazily through ``__getattr__`` so ``from action_machine.model.base_result``
does not import :mod:`action_machine.graph_model` eagerly (avoids cycles with graph edges).

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

import importlib
from typing import TYPE_CHECKING, Any

from action_machine.model.base_action import BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from action_machine.model.base_schema import BaseSchema
from action_machine.model.base_state import BaseState
from action_machine.model.params_stub import ParamsStub
from action_machine.model.result_stub import ResultStub

if TYPE_CHECKING:
    from action_machine.graph_model.inspectors.action_graph_node_inspector import (
        ActionGraphNodeInspector,
    )
    from action_machine.graph_model.inspectors.params_graph_node_inspector import (
        ParamsGraphNodeInspector,
    )
    from action_machine.graph_model.inspectors.result_graph_node_inspector import (
        ResultGraphNodeInspector,
    )
    from action_machine.graph_model.nodes.action_graph_node import ActionGraphNode
    from action_machine.graph_model.nodes.checker_graph_node import CheckerGraphNode
    from action_machine.graph_model.nodes.compensator_graph_node import CompensatorGraphNode
    from action_machine.graph_model.nodes.error_handler_graph_node import ErrorHandlerGraphNode
    from action_machine.graph_model.nodes.params_graph_node import ParamsGraphNode
    from action_machine.graph_model.nodes.regular_aspect_graph_node import RegularAspectGraphNode
    from action_machine.graph_model.nodes.result_graph_node import ResultGraphNode
    from action_machine.graph_model.nodes.summary_aspect_graph_node import SummaryAspectGraphNode


_LAZY_GRAPH_EXPORTS: dict[str, tuple[str, str]] = {
    "ActionGraphNode": ("action_machine.graph_model.nodes.action_graph_node", "ActionGraphNode"),
    "ActionGraphNodeInspector": (
        "action_machine.graph_model.inspectors.action_graph_node_inspector",
        "ActionGraphNodeInspector",
    ),
    "CheckerGraphNode": ("action_machine.graph_model.nodes.checker_graph_node", "CheckerGraphNode"),
    "CompensatorGraphNode": (
        "action_machine.graph_model.nodes.compensator_graph_node",
        "CompensatorGraphNode",
    ),
    "ErrorHandlerGraphNode": (
        "action_machine.graph_model.nodes.error_handler_graph_node",
        "ErrorHandlerGraphNode",
    ),
    "ParamsGraphNode": ("action_machine.graph_model.nodes.params_graph_node", "ParamsGraphNode"),
    "ParamsGraphNodeInspector": (
        "action_machine.graph_model.inspectors.params_graph_node_inspector",
        "ParamsGraphNodeInspector",
    ),
    "RegularAspectGraphNode": (
        "action_machine.graph_model.nodes.regular_aspect_graph_node",
        "RegularAspectGraphNode",
    ),
    "ResultGraphNode": ("action_machine.graph_model.nodes.result_graph_node", "ResultGraphNode"),
    "ResultGraphNodeInspector": (
        "action_machine.graph_model.inspectors.result_graph_node_inspector",
        "ResultGraphNodeInspector",
    ),
    "SummaryAspectGraphNode": (
        "action_machine.graph_model.nodes.summary_aspect_graph_node",
        "SummaryAspectGraphNode",
    ),
}


def __getattr__(name: str) -> Any:
    """Lazy graph re-exports — avoid importing :mod:`action_machine.graph_model` when loading base stubs."""
    spec = _LAZY_GRAPH_EXPORTS.get(name)
    if spec is not None:
        mod_path, attr = spec
        module = importlib.import_module(mod_path)
        return getattr(module, attr)
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
    "ParamsStub",
    "RegularAspectGraphNode",
    "ResultGraphNode",
    "ResultGraphNodeInspector",
    "ResultStub",
    "SummaryAspectGraphNode",
]
