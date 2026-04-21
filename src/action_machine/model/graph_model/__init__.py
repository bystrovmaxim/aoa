# src/action_machine/model/graph_model/__init__.py
"""
Interchange graph node types for the model axis.

Import concrete symbols from submodules, e.g.
``from action_machine.model.graph_model.action_graph_node import ActionGraphNode``,
to avoid import cycles with :mod:`action_machine.domain` during
:mod:`action_machine.model` package initialization.
"""

from __future__ import annotations

import importlib
from typing import Any

# Public names are resolved lazily via __getattr__; they are not module-level assignments here.
# pylint: disable=undefined-all-variable
__all__ = [
    "ActionGraphNode",
    "ActionGraphNodeInspector",
    "CallableKind",
    "CompensatorGraphNode",
    "ErrorHandlerGraphNode",
    "ParamsGraphNode",
    "ParamsGraphNodeInspector",
    "RegularAspectGraphNode",
    "ResultGraphNode",
    "ResultGraphNodeInspector",
    "SummaryAspectGraphNode",
]

_LAZY: dict[str, str] = {
    "ActionGraphNode": "action_machine.model.graph_model.action_graph_node",
    "ActionGraphNodeInspector": "action_machine.model.graph_model.action_graph_node_inspector",
    "CompensatorGraphNode": "action_machine.model.graph_model.compensator_graph_node",
    "ErrorHandlerGraphNode": "action_machine.model.graph_model.error_handler_graph_node",
    "CallableKind": "action_machine.introspection_tools.intent_introspection",
    "ParamsGraphNode": "action_machine.model.graph_model.params_graph_node",
    "ParamsGraphNodeInspector": "action_machine.model.graph_model.params_graph_node_inspector",
    "RegularAspectGraphNode": "action_machine.model.graph_model.regular_aspect_graph_node",
    "ResultGraphNode": "action_machine.model.graph_model.result_graph_node",
    "SummaryAspectGraphNode": "action_machine.model.graph_model.summary_aspect_graph_node",
    "ResultGraphNodeInspector": "action_machine.model.graph_model.result_graph_node_inspector",
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
