# packages/aoa-action-machine/src/aoa/action_machine/graph/edges/application_graph_edge.py
"""
ApplicationGraphEdge — AGGREGATION from host class → application interchange node.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Centralize ``edge_name=\"application\"`` plus fixed DAG semantics for edges whose
target is :class:`~aoa.action_machine.graph.nodes.application_graph_node.ApplicationGraphNode`
(``NODE_TYPE`` ``\"Application\"``). Requires explicit ``application_cls`` in the
constructor. Not wired by coordinators or intent resolvers yet—callers build
edges manually when needed.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    host ``type``  +  ``application_cls``  ──>  ``ApplicationGraphEdge``  ──>  ``target_node_id`` = dotted app class id

"""

from __future__ import annotations

from typing import Any, TypeVar

from aoa.action_machine.application.application import Application
from aoa.action_machine.graph.core.aggregation_graph_edge import AggregationGraphEdge
from aoa.action_machine.system_core.type_introspection import TypeIntrospection

TApplication = TypeVar("TApplication", bound=Application)


class ApplicationGraphEdge(AggregationGraphEdge):
    """
    AI-CORE-BEGIN
    ROLE: Typed aggregation edge ``host → application`` marker graph node.
    CONTRACT: ``edge_name`` ``application``; ``target_node`` is for future coordinator wiring (``None`` stub).
    INVARIANTS: Frozen via ``AggregationGraphEdge`` base.
    AI-CORE-END
    """

    def __init__(
        self,
        application_cls: type[TApplication],
    ) -> None:
        super().__init__(
            edge_name="application",
            is_dag=True,
            target_node_id=TypeIntrospection.full_qualname(application_cls),
            target_node=None,
        )

    def to_dict(self, *, source_id: str) -> dict[str, Any]:
        return {
            "source_id": source_id,
            "target_id": self.target_node_id,
            "type": self.edge_name,
            "relationship": self.edge_relationship.archimate_name,
            "is_dag": self.is_dag,
            "properties": {},
        }
