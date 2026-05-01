# src/action_machine/graph_model/edges/__init__.py
"""
Typed interchange edges for the model-axis Action host (aggregation, association, composition).

Public names resolve lazily via ``__getattr__`` so importing one edge submodule does not
execute unrelated edge modules (avoids cycles with graph nodes).

Import concrete symbols from leaf modules when you prefer explicit paths, e.g.
``from action_machine.graph_model.edges.field_graph_edge import FieldGraphEdge``.
"""

from __future__ import annotations

import importlib
from typing import Any

# pylint: disable=undefined-all-variable
__all__ = [
    "CheckerGraphEdge",
    "CompensatorGraphEdge",
    "ConnectionGraphEdge",
    "DependsGraphEdge",
    "DomainGraphEdge",
    "EntityGraphEdge",
    "ErrorHandlerGraphEdge",
    "FieldGraphEdge",
    "ParamsGraphEdge",
    "PropertyGraphEdge",
    "RegularAspectGraphEdge",
    "RequiredContextGraphEdge",
    "ResultGraphEdge",
    "RoleGraphEdge",
    "SummaryAspectGraphEdge",
]

_LAZY: dict[str, str] = {
    "CompensatorGraphEdge": "action_machine.graph_model.edges.compensator_graph_edge",
    "ConnectionGraphEdge": "action_machine.graph_model.edges.connection_graph_edge",
    "DependsGraphEdge": "action_machine.graph_model.edges.depends_graph_edge",
    "DomainGraphEdge": "action_machine.graph_model.edges.domain_graph_edge",
    "EntityGraphEdge": "action_machine.graph_model.edges.entity_graph_edge",
    "ErrorHandlerGraphEdge": "action_machine.graph_model.edges.error_handler_graph_edge",
    "FieldGraphEdge": "action_machine.graph_model.edges.field_graph_edge",
    "CheckerGraphEdge": "action_machine.graph_model.edges.checker_graph_edge",
    "ParamsGraphEdge": "action_machine.graph_model.edges.params_graph_edge",
    "PropertyGraphEdge": "action_machine.graph_model.edges.property_graph_edge",
    "RegularAspectGraphEdge": "action_machine.graph_model.edges.regular_aspect_graph_edge",
    "RequiredContextGraphEdge": "action_machine.graph_model.edges.required_context_graph_edge",
    "RoleGraphEdge": "action_machine.graph_model.edges.role_graph_edge",
    "ResultGraphEdge": "action_machine.graph_model.edges.result_graph_edge",
    "SummaryAspectGraphEdge": "action_machine.graph_model.edges.summary_aspect_graph_edge",
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
