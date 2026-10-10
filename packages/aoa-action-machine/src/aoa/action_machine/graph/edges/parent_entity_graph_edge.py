# packages/aoa-action-machine/src/aoa/action_machine/graph/edges/parent_entity_graph_edge.py
"""
ParentEntityGraphEdge — GENERALIZATION (``parent_entity``) from an extension entity → its head.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

An extension entity is a **variant of** its head, and the diagram draws that as inheritance: the
extension points at the head through the field it declares for the axis. This edge is that
statement, one per declared alternative, and it is the reverse direction of
:class:`~aoa.action_machine.graph.edges.entity_specialization_graph_edge.EntitySpecializationGraphEdge`
— the head says "the continuation is one of these", each extension says "I am one of those".

Four properties travel with it, and each answers a question a picture or a consumer asks: which
field of the extension the axis came through, which field of the head it answers to, which code
the extension declares, and which head it continues. Without them the edge would say "inherits
something" and leave the reader to work out what.

It is a **generalization**, like ``parent_action`` / ``parent_role`` / ``parent_domain``, and that
relationship is what keeps it out of the full-graph payload: that payload strips ``Generalization``
because inheritance is structure rather than a link between two rows. The axis itself still reaches
the payload, as ``entity_specialization`` from the head.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    the head declares an axis          the extension declares a reverse field
    Specialization[A | B | C]    ──►   Generalization[Head] + Classifier(code)
              │                                        │
              └────────► each alternative produces exactly one ◄────────┘
                                   parent_entity edge
                        field_name · inverse_field · classifier_value · head_entity_id

═══════════════════════════════════════════════════════════════════════════════
LIFECYCLE (IMPORT VS BUILD VS RUNTIME)
═══════════════════════════════════════════════════════════════════════════════

- **Import**: the edge class is defined.
- **Build**: the extension's owner emits one edge per axis it is an alternative of; the
  coordinator wires the target and refuses an edge whose target is not a node.
- **Runtime**: read-only interchange data, excluded from the full-graph payload by relationship.

"""

from __future__ import annotations

from typing import Any

from aoa.action_machine.graph.core.generalization_graph_edge import GeneralizationGraphEdge
from aoa.action_machine.intents.entity.entity_specialization_intent_resolver import (
    EntitySpecializationIntentResolver,
    gather_entity_specialization_intent_resolvers,
    read_declared_code,
    read_reverse_declarations,
    reverse_head,
)
from aoa.action_machine.system_core.type_introspection import TypeIntrospection


class ParentEntityGraphEdge(GeneralizationGraphEdge):
    """
    AI-CORE-BEGIN
    ROLE: Generalization edge from one extension entity to the head whose axis it is a variant of.
    CONTRACT: ``edge_name`` ``parent_entity``; fixed ``GENERALIZATION`` relationship, so the full-graph payload excludes it; ``is_dag`` False; properties carry the extension's field, the head's field, the declared code and the head's id.
    INVARIANTS: One edge per declared alternative; the code is read from the extension's own declaration, never from the head's list alone.
    AI-CORE-END
    """

    EDGE_NAME = "parent_entity"

    def __init__(
        self,
        *,
        head_entity: type[Any],
        axis: EntitySpecializationIntentResolver,
        extension_cls: type[Any],
        extension_field: str,
        target_node: Any = None,
    ) -> None:
        """
        Args:
            head_entity: The head this extension is a variant of.
            axis: The head's parsed axis, which carries the classifier field name.
            extension_cls: The extension class, which declares the code for this axis.
            extension_field: The extension's own field that points at the head.
            target_node: Wired by the coordinator while the graph is built.
        """
        super().__init__(
            edge_name=ParentEntityGraphEdge.EDGE_NAME,
            is_dag=False,
            target_node_id=TypeIntrospection.full_qualname(head_entity),
            target_node=target_node,
            properties={
                "field_name": extension_field,
                "inverse_field": axis.field_name,
                "classifier_value": read_declared_code(extension_cls, head_entity, field_name=extension_field),
                "head_entity_id": TypeIntrospection.full_qualname(head_entity),
            },
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
                "inverse_field": str(self.properties["inverse_field"]),
                "classifier_value": str(self.properties["classifier_value"]),
                "head_entity_id": str(self.properties["head_entity_id"]),
            },
        }

    @staticmethod
    def get_entity_generalization_edges(extension_cls: type) -> list[ParentEntityGraphEdge]:
        """
        Return one generalization edge per axis ``extension_cls`` is an alternative of.

        The edge is built from **both** sides at once, and only when they agree: the head must
        declare an axis whose alternatives include this class, and the class must carry a reverse
        field for that head. A class that merely inherits, or carries a ``Generalization``
        container for a class that declares no axis, produces nothing — which is what keeps an
        ordinary inheritance relationship out of this family.
        """
        model_fields = getattr(extension_cls, "model_fields", None)
        if not model_fields:
            return []

        heads = {
            head
            for info in model_fields.values()
            for head in (reverse_head(extension_cls, info),)
            if head is not None
        }

        edges: list[ParentEntityGraphEdge] = []
        for head in sorted(heads, key=TypeIntrospection.full_qualname):
            for axis in gather_entity_specialization_intent_resolvers(head):
                if extension_cls not in axis.alternatives:
                    continue
                for field_name, _ in read_reverse_declarations(extension_cls, head):
                    if axis.inverse_field and field_name != axis.inverse_field:
                        continue
                    edges.append(
                        ParentEntityGraphEdge(
                            head_entity=head,
                            axis=axis,
                            extension_cls=extension_cls,
                            extension_field=field_name,
                        )
                    )
        return edges


__all__ = ["ParentEntityGraphEdge"]
