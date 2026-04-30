# src/action_machine/model/graph_model/edges/__init__.py
"""
Typed interchange edges for the model-axis Action host (aggregation, association, composition).

Import from submodules to avoid pulling unused graph-node classes into every caller.
"""

from __future__ import annotations

from action_machine.model.graph_model.edges.compensator_graph_edge import (
    CompensatorGraphEdge,
)
from action_machine.model.graph_model.edges.connection_graph_edge import ConnectionGraphEdge
from action_machine.model.graph_model.edges.depends_graph_edge import DependsGraphEdge
from action_machine.model.graph_model.edges.error_handler_graph_edge import (
    ErrorHandlerGraphEdge,
)
from action_machine.model.graph_model.edges.field_graph_edge import FieldGraphEdge
from action_machine.model.graph_model.edges.params_graph_edge import ParamsGraphEdge
from action_machine.model.graph_model.edges.property_graph_edge import PropertyGraphEdge
from action_machine.model.graph_model.edges.regular_aspect_graph_edge import (
    RegularAspectGraphEdge,
)
from action_machine.model.graph_model.edges.result_graph_edge import ResultGraphEdge
from action_machine.model.graph_model.edges.summary_aspect_graph_edge import (
    SummaryAspectGraphEdge,
)

__all__ = [
    "CompensatorGraphEdge",
    "ConnectionGraphEdge",
    "DependsGraphEdge",
    "ErrorHandlerGraphEdge",
    "FieldGraphEdge",
    "ParamsGraphEdge",
    "PropertyGraphEdge",
    "RegularAspectGraphEdge",
    "ResultGraphEdge",
    "SummaryAspectGraphEdge",
]
