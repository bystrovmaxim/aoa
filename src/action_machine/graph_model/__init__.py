# src/action_machine/graph_model/__init__.py
"""
Interchange graph node types for the model axis.

Import concrete symbols from submodules, e.g.
``from action_machine.graph_model.nodes.action_graph_node import ActionGraphNode``,
to avoid import cycles with :mod:`action_machine.domain` and with :mod:`action_machine.model`
base imports (graph lives alongside ``model``, not inside it).
"""

from __future__ import annotations

import importlib
from typing import Any

# Public names are resolved lazily via __getattr__; they are not module-level assignments here.
# pylint: disable=undefined-all-variable
__all__ = [
    "ActionGraphNode",
    "ActionGraphNodeInspector",
    "CheckerGraphNode",
    "CompensatorGraphNode",
    "ErrorHandlerGraphNode",
    "ParamsGraphNode",
    "ParamsGraphNodeInspector",
    "RegularAspectGraphNode",
    "RequiredContextGraphNode",
    "ResultGraphNode",
    "ResultGraphNodeInspector",
    "SummaryAspectGraphNode",
]

_LAZY: dict[str, str] = {
    "ActionGraphNode": "action_machine.graph_model.nodes.action_graph_node",
    "ActionGraphNodeInspector": "action_machine.graph_model.inspectors.action_graph_node_inspector",
    "CompensatorGraphNode": "action_machine.graph_model.nodes.compensator_graph_node",
    "ErrorHandlerGraphNode": "action_machine.graph_model.nodes.error_handler_graph_node",
    "CheckerGraphNode": "action_machine.graph_model.nodes.checker_graph_node",
    "ParamsGraphNode": "action_machine.graph_model.nodes.params_graph_node",
    "ParamsGraphNodeInspector": "action_machine.graph_model.inspectors.params_graph_node_inspector",
    "RegularAspectGraphNode": "action_machine.graph_model.nodes.regular_aspect_graph_node",
    "RequiredContextGraphNode": "action_machine.graph_model.nodes.required_context_graph_node",
    "ResultGraphNode": "action_machine.graph_model.nodes.result_graph_node",
    "SummaryAspectGraphNode": "action_machine.graph_model.nodes.summary_aspect_graph_node",
    "ResultGraphNodeInspector": "action_machine.graph_model.inspectors.result_graph_node_inspector",
}


def __getattr__(name: str) -> Any:
    mod_path = _LAZY.get(name)
    if mod_path is None:
        msg = f"module {__name__!r} has no attribute {name!r}"
        raise AttributeError(msg)
    module = importlib.import_module(mod_path)
    value = getattr(module, name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(__all__)
