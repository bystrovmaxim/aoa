# src/action_machine/model/graph_model/inspectors/__init__.py
"""
Graph model inspectors — node inspectors for action model graph vertices.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Groups graph-node inspectors that walk action model type axes and emit concrete
interchange vertices.
"""

from __future__ import annotations

import importlib
from typing import Any

# Public names resolve lazily via ``__getattr__``; not assigned at import time.
# pylint: disable=undefined-all-variable
__all__ = [
    "ActionGraphNodeInspector",
    "ParamsGraphNodeInspector",
    "ResultGraphNodeInspector",
]

_LAZY: dict[str, str] = {
    "ActionGraphNodeInspector": "action_machine.model.graph_model.inspectors.action_graph_node_inspector",
    "ParamsGraphNodeInspector": "action_machine.model.graph_model.inspectors.params_graph_node_inspector",
    "ResultGraphNodeInspector": "action_machine.model.graph_model.inspectors.result_graph_node_inspector",
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
