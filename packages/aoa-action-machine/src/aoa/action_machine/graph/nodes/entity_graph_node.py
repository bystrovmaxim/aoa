# packages/aoa-action-machine/src/aoa/action_machine/graph/nodes/entity_graph_node.py
"""
EntityGraphNode — minimal interchange node for ``BaseEntity`` subclasses.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Materializes a frozen :class:`~aoa.action_machine.graph.core.base_graph_node.BaseGraphNode` from an
entity **class** object: stable ``id`` (dotted path), ``node_type="Entity"``,
``label`` from the class name, ``properties`` from :meth:`~aoa.action_machine.intents.entity.entity_intent_resolver.EntityIntentResolver.resolve_description`,
a ``domain`` edge built by :class:`~aoa.action_machine.graph.edges.domain_graph_edge.DomainGraphEdge`,
``entity_relation`` edges from :class:`~aoa.action_machine.graph.edges.entity_graph_edge.EntityGraphEdge`,
:class:`~aoa.action_machine.graph.edges.lifecycle_graph_edge.LifeCycleGraphEdge`
lifecycle compositions (:attr:`lifecycles`), and ``entity_field`` compositions from
:meth:`~aoa.action_machine.graph.edges.entity_field_graph_edge.EntityFieldGraphEdge.get_entity_field_edges`
to :class:`~aoa.action_machine.graph.nodes.entity_field_graph_node.EntityFieldGraphNode`
for each scalar model field (see :attr:`entity_field_edges`), and ``entity_specialization`` edges from
:class:`~aoa.action_machine.graph.edges.entity_specialization_graph_edge.EntitySpecializationGraphEdge`
for every alternative of every declared specialization axis (see :attr:`specializations`).

State rows belong to each wired :class:`~aoa.action_machine.graph.nodes.lifecycle_graph_node.LifeCycleGraphNode`;
the entity row contributes lifecycle vertices only.

(``@entity`` ``domain``: :meth:`~aoa.action_machine.intents.entity.entity_intent_resolver.EntityIntentResolver.resolve_domain_type`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar, TypeVar, cast

from aoa.action_machine.domain.entity import BaseEntity
from aoa.action_machine.graph.core.base_graph_edge import BaseGraphEdge
from aoa.action_machine.graph.core.base_graph_node import BaseGraphNode
from aoa.action_machine.graph.edges.domain_graph_edge import DomainGraphEdge
from aoa.action_machine.graph.edges.entity_field_graph_edge import EntityFieldGraphEdge
from aoa.action_machine.graph.edges.entity_graph_edge import EntityGraphEdge
from aoa.action_machine.graph.edges.entity_reference_graph_edge import EntityReferenceGraphEdge
from aoa.action_machine.graph.edges.entity_specialization_graph_edge import (
    EntitySpecializationGraphEdge,
)
from aoa.action_machine.graph.edges.lifecycle_graph_edge import LifeCycleGraphEdge
from aoa.action_machine.graph.edges.parent_entity_graph_edge import ParentEntityGraphEdge
from aoa.action_machine.intents.entity.entity_intent_resolver import EntityIntentResolver
from aoa.action_machine.system_core.type_introspection import TypeIntrospection

TEntity = TypeVar("TEntity", bound=BaseEntity)


def entity_kind_of(entity_cls: type) -> str:
    """The word a class's kind base class declares through its own name."""
    for base in entity_cls.__mro__:
        if BaseEntity in base.__bases__:
            return base.__name__.removeprefix("Base").removesuffix("Entity").lower()
    raise TypeError(
        f"{entity_cls.__name__} carries no kind base class, so its row cannot state a kind; "
        f"inherit one of the six base classes instead of BaseEntity itself."
    )


@dataclass(init=False, frozen=True)
class EntityGraphNode(BaseGraphNode[type[TEntity]]):
    """
    AI-CORE-BEGIN
    ROLE: Interchange bridge for ``BaseEntity`` host classes.
    CONTRACT: Dotted-path ``id``, ``__name__`` label; :attr:`NODE_TYPE`; :attr:`domain` / :attr:`relations` / :attr:`references` / :attr:`lifecycles` / :attr:`entity_field_edges` from scalar fields; :meth:`get_all_edges` lists domain, relations, dictionary references, lifecycle compositions, and ``entity_field`` edges; :meth:`get_companion_nodes` returns lifecycle targets and :class:`EntityFieldGraphNode` targets. JSON omits nested ``fields``/``field_order`` on the entity row.
    AI-CORE-END
    """

    NODE_TYPE: ClassVar[str] = "Entity"
    domain: DomainGraphEdge = field(init=False, repr=False, compare=False)
    relations: list[EntityGraphEdge] = field(init=False)
    references: list[EntityReferenceGraphEdge] = field(init=False)
    specializations: list[EntitySpecializationGraphEdge] = field(init=False)
    generalizations: list[ParentEntityGraphEdge] = field(init=False)
    lifecycles: list[LifeCycleGraphEdge] = field(init=False)
    entity_field_edges: list[EntityFieldGraphEdge] = field(init=False)

    def __init__(self, entity_cls: type[TEntity]) -> None:
        description = EntityIntentResolver.resolve_description(entity_cls)
        field_edges = EntityFieldGraphEdge.get_entity_field_edges(entity_cls)
        kind = entity_kind_of(entity_cls)
        properties: dict[str, Any] = {"description": description, "entity_kind": kind}
        if kind == "enum":
            declared = cast(Any, entity_cls).members
            properties["values"] = [member.to_reference() for member in declared]
        super().__init__(
            node_id=TypeIntrospection.full_qualname(entity_cls),
            node_type=EntityGraphNode.NODE_TYPE,
            label=entity_cls.__name__,
            properties=properties,
            node_obj=entity_cls,
        )
        object.__setattr__(self, "domain", DomainGraphEdge.from_entity_declared_host(entity_cls, self))
        object.__setattr__(self, "relations", EntityGraphEdge.get_entity_relation_edges(entity_cls))
        object.__setattr__(self, "references", EntityReferenceGraphEdge.get_entity_reference_edges(entity_cls))
        object.__setattr__(
            self,
            "specializations",
            EntitySpecializationGraphEdge.get_entity_specialization_edges(entity_cls),
        )
        object.__setattr__(
            self,
            "generalizations",
            ParentEntityGraphEdge.get_entity_generalization_edges(entity_cls),
        )
        object.__setattr__(self, "lifecycles", LifeCycleGraphEdge.get_lifecycle_edges(entity_cls))
        object.__setattr__(self, "entity_field_edges", field_edges)

    def to_dict(self) -> dict[str, Any]:
        properties: dict[str, Any] = {
            "description": str(self.properties["description"]),
            "entity_kind": str(self.properties["entity_kind"]),
        }
        if "values" in self.properties:
            properties["values"] = self.properties["values"]
        return {"id": self.node_id, "type": self.node_type, "label": self.label, "properties": properties}

    def get_companion_nodes(self) -> list[BaseGraphNode[Any]]:
        """Lifecycle field targets and scalar ``EntityField`` vertices."""
        lifecycle_targets = [target for edge in self.lifecycles if (target := edge.target_node) is not None]
        field_targets = [edge.target_node for edge in self.entity_field_edges if edge.target_node is not None]
        return [*lifecycle_targets, *field_targets]

    def get_all_edges(self) -> list[BaseGraphEdge]:
        """Return ``domain``, relations, references, specializations, generalizations, lifecycles and fields."""
        return [
            self.domain,
            *self.relations,
            *self.references,
            *self.specializations,
            *self.generalizations,
            *self.lifecycles,
            *self.entity_field_edges,
        ]
