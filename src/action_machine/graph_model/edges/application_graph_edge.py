# src/action_machine/graph_model/edges/application_graph_edge.py
"""
ApplicationGraphEdge — AGGREGATION from host class → application interchange node.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Centralize ``edge_name=\"application\"`` plus fixed DAG semantics for edges whose
target is :class:`~action_machine.graph_model.nodes.application_graph_node.ApplicationGraphNode`
(``NODE_TYPE`` ``\"Application\"``). Requires explicit ``application_cls`` in the
constructor. Not wired by coordinators or intent resolvers yet—callers build
edges manually when needed.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    host ``type``  +  ``application_cls``  ──>  ``ApplicationGraphEdge``  ──>  ``target_node_id`` = dotted app class id

"""

from __future__ import annotations

from typing import TypeVar

from action_machine.application.application import Application
from action_machine.system_core.type_introspection import TypeIntrospection
from graph.aggregation_graph_edge import AggregationGraphEdge

TApplication = TypeVar("TApplication", bound=Application)


class ApplicationGraphEdge(AggregationGraphEdge):
    """
    AI-CORE-BEGIN
    ROLE: Typed aggregation edge ``host → application`` marker vertex.
    CONTRACT: ``edge_name`` ``application``; ``target_node`` is for future coordinator wiring (``None`` stub).
    INVARIANTS: Frozen via ``AggregationGraphEdge`` base; ``source_cls`` is API-only (not stored on the edge payload).
    AI-CORE-END
    """

    def __init__(
        self,
        source_cls: type,
        application_cls: type[TApplication],
    ) -> None:
        super().__init__(
            edge_name="application",
            is_dag=True,
            target_node_id=TypeIntrospection.full_qualname(application_cls),
            target_node=None,
        )
