# packages/aoa-action-machine/src/aoa/action_machine/graph/edges/entity_specialization_graph_edge.py
"""
EntitySpecializationGraphEdge — one head→alternative edge per declared alternative.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A head field that points at one of N extension entities becomes **N edges**, one per
alternative, so a consumer that walks edges reaches every target a foreign-key walk
would look for.

The field itself stays a **column**: its ``EntityField`` row belongs in the diagram
exactly like every other field, because a reader has to see that the row has a
continuation at all. The edges carry the meaning of the choice — which codes exist,
which code selects which class, which field decides — and nothing is duplicated into a
second vertex for the field. A vertex of its own would collide with the column row,
since both would be identified by the same entity and field name.

Each edge carries the code that selects its own target, its position in the declared
order, and the whole ordered code list. The list is repeated on every edge **on
purpose**: it is the declaration's order, and a graph consumer that has one edge in
hand must be able to reconstruct the alternatives without a second lookup, and without
re-sorting what the developer wrote.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    EntityGraphNode  ──entity_specialization[field]──►  every alternative's EntityGraphNode
        │                                                    (one edge per alternative)
        └─ properties: field_name, classifier_field, classifier_value,
                       alternative_index, alternatives[], description, deprecated

The relationship is ``Association``, like every other entity relation, so these edges
stay in the full-graph payload. The reverse direction — extension to head — is the
generalization edge family, which that payload excludes by design.

═══════════════════════════════════════════════════════════════════════════════
LIFECYCLE (IMPORT VS BUILD VS RUNTIME)
═══════════════════════════════════════════════════════════════════════════════

- **Import**: the class is defined.
- **Build**: the owning ``EntityGraphNode`` creates one edge per alternative; the
  coordinator wires ``target_node`` and refuses an edge whose target is not a node.
- **Runtime**: read-only interchange data.

"""

from __future__ import annotations

from typing import Any

from aoa.action_machine.graph.core.association_graph_edge import AssociationGraphEdge
from aoa.action_machine.graph.core.base_graph_node import BaseGraphNode
from aoa.action_machine.intents.entity.entity_intent_resolver import EntityIntentResolver
from aoa.action_machine.intents.entity.entity_specialization_intent_resolver import (
    EntitySpecializationIntentResolver,
)
from aoa.action_machine.system_core.type_introspection import TypeIntrospection


def _alternative_identifiers(axis: EntitySpecializationIntentResolver) -> list[str]:
    """Return ``"<code> -> <qualname>"`` for every alternative, in declaration order."""
    return [f"{code} -> {TypeIntrospection.full_qualname(axis.code_to_target[code])}" for code in axis.codes]


def _alternative_labels(axis: EntitySpecializationIntentResolver) -> list[str]:
    """
    Return the display name of every alternative, in the same order as ``alternatives``.

    A class name in a diagram is read, not resolved, so the shared ``Entity`` suffix is dropped:
    every table in the picture carries it, it distinguishes nothing, and it costs width in the
    narrowest column of the table. This is a display string and nothing parses it back — the
    qualified name stays in ``alternatives`` for anything that has to resolve a class.
    """
    labels: list[str] = []
    for code in axis.codes:
        name = axis.code_to_target[code].__name__
        labels.append(f"{name[: -len('Entity')]} ({code})" if name.endswith("Entity") else f"{name} ({code})")
    return labels


def _specialization_properties(
    axis: EntitySpecializationIntentResolver,
    *,
    code: str,
    index: int,
) -> dict[str, Any]:
    """Return the property set shared by every edge of one axis."""
    return {
        "field_name": axis.field_name,
        "classifier_field": axis.classifier_field,
        "classifier_value": code,
        "alternative_index": index,
        "alternatives": _alternative_identifiers(axis),
        "labels": _alternative_labels(axis),
        "relation_type": "specialization",
        "cardinality": "one",
        "description": axis.description,
        "has_inverse": bool(axis.inverse_field),
        "deprecated": axis.deprecated,
    }


class EntitySpecializationGraphEdge(AssociationGraphEdge):
    """
    AI-CORE-BEGIN
        ROLE: Typed association edge from a head entity to one of its declared alternatives.
        CONTRACT: ``edge_name`` ``entity_specialization``; ``is_dag`` False; the coordinator wires ``target_node``; ``properties`` carry the field, the classifier, this edge's code, its position and the whole ordered code list.
        INVARIANTS: One edge per alternative, in declaration order; frozen via ``AssociationGraphEdge``.
        AI-CORE-END
    """

    EDGE_NAME = "entity_specialization"

    def __init__(
        self,
        *,
        target_node_id: str,
        axis: EntitySpecializationIntentResolver,
        code: str,
        index: int,
        target_node: BaseGraphNode[Any] | None = None,
    ) -> None:
        """
        Args:
            target_node_id: Interchange id of the alternative this edge points at.
            axis: The parsed axis the edge belongs to.
            code: The declared code that selects this alternative.
            index: Position of the alternative in the declared order.
            target_node: Wired by the coordinator while the graph is built.
        """
        super().__init__(
            edge_name=EntitySpecializationGraphEdge.EDGE_NAME,
            is_dag=False,
            target_node_id=target_node_id,
            target_node=target_node,
            properties=_specialization_properties(axis, code=code, index=index),
        )

    def to_dict(self, *, source_id: str) -> dict[str, Any]:
        return {
            "source_id": source_id,
            "target_id": self.target_node_id,
            "type": self.edge_name,
            "relationship": self.edge_relationship.archimate_name,
            "is_dag": self.is_dag,
            "properties": {
                "field_name": str(self.properties["field_name"]),
                "classifier_field": str(self.properties["classifier_field"]),
                "classifier_value": str(self.properties["classifier_value"]),
                "alternative_index": int(self.properties["alternative_index"]),
                "alternatives": [str(item) for item in self.properties["alternatives"]],
                "labels": [str(item) for item in self.properties["labels"]],
                "relation_type": str(self.properties["relation_type"]),
                "cardinality": str(self.properties["cardinality"]),
                "description": str(self.properties["description"]),
                "has_inverse": bool(self.properties["has_inverse"]),
                "deprecated": bool(self.properties["deprecated"]),
            },
        }

    @staticmethod
    def get_entity_specialization_edges(entity_cls: type) -> list[EntitySpecializationGraphEdge]:
        """Return one edge per alternative for every non-omitted axis on ``entity_cls``."""
        edges: list[EntitySpecializationGraphEdge] = []
        for axis in EntityIntentResolver.resolve_entity_specializations(entity_cls):
            if axis.omit_graph_edge:
                continue
            for index, code in enumerate(axis.codes):
                target = axis.code_to_target.get(code)
                if target is None:
                    continue
                edges.append(
                    EntitySpecializationGraphEdge(
                        axis=axis,
                        code=code,
                        index=index,
                        target_node_id=TypeIntrospection.full_qualname(target),
                        target_node=None,
                    )
                )
        return edges
