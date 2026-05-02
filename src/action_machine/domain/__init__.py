"""
Domain package public exports for bounded-context modeling.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

This package provides the declarative domain layer: entities, fields, relations,
and lifecycle state machines. It intentionally contains no transport or storage
adapters. The same entity type can be hydrated from any backend; persistence is
owned by resource managers, not by the entity class.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

Domain declarations follow the same grammar pipeline as other ActionMachine
facets: ``intent -> decorator -> scratch -> inspector -> coordinator``.

    @entity  ──writes──>  _entity_info  (scratch)
         │
         │ requires
         v
    EntityIntent  (marker: “this class declares the @entity grammar”)
         │
         │ at coordinator.build() / graph export
         v
    ``EntityIntentResolver`` + relation / lifecycle intent resolvers  ──read scratch + ``model_fields``──> metadata
         │
         v
    interchange graph from ``NodeGraphCoordinator`` / ``EntityGraphNode`` rows  (entities, domains, relation edges, …)

═══════════════════════════════════════════════════════════════════════════════
PACKAGE CONTENTS
═══════════════════════════════════════════════════════════════════════════════

Domains:
    BaseDomain — abstract base for all domain marker classes.
    DomainGraphNode — interchange node for a concrete ``BaseDomain`` class (see :mod:`action_machine.graph_model.nodes`).

Entities:
    BaseEntity — abstract base for all entities (frozen, `extra="forbid"`).
    EntityIntent — marker mixin: the type declares participation in the
    ``@entity`` grammar (facet / inspector at ``NodeGraphCoordinator.build()``).
    entity — class decorator declaring an entity (`_entity_info`).

State machines:
    Lifecycle — declarative finite-state machine template (import-time fluent API).
    StateType — enum: INITIAL, INTERMEDIATE, FINAL.
    StateInfo — frozen dataclass for one state’s metadata.

Relations between entities:
    CompositeOne/Many, AggregateOne/Many, AssociationOne/Many — typed containers.
    RelationType — ownership kind (composition / aggregation / association).
    Inverse, NoInverse, Rel — markers and default for relation metadata.

Utilities:
    build — hydrate an entity from flat dict data (optional typed mapper).
    make — test helper with simple auto-defaults for primitive fields.

Exceptions:
    FieldNotLoadedError, RelationNotLoadedError,
    EntityDecoratorError, LifecycleValidationError.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    from pydantic import Field

    from action_machine.domain import (
        BaseDomain,
        BaseEntity,
        Lifecycle,
        AssociationOne,
        CompositeMany,
        Inverse,
        Rel,
        build,
        entity,
    )

    class ShopDomain(BaseDomain):
        name = "shop"
        description = "E-commerce shop bounded context"

    @entity(description="Customer order", domain=ShopDomain)
    class OrderEntity(BaseEntity):
        lifecycle = (
            Lifecycle("Order lifecycle")
            .state("new", "New").to("confirmed", "cancelled").initial()
            .state("confirmed", "Confirmed").to("shipped").intermediate()
            .state("delivered", "Delivered").final()
            .state("cancelled", "Cancelled").final()
        )
        id: str = Field(description="Order identifier")
        amount: float = Field(description="Order total", ge=0)

    order = build({"id": "123", "amount": 100.0}, OrderEntity)
"""

# Deferred graph interchange symbols are bound in ``__getattr__``.
# pylint: disable=undefined-all-variable

from action_machine.domain.base_domain import BaseDomain
from action_machine.domain.entity import BaseEntity
from action_machine.domain.exceptions import (
    EntityDecoratorError,
    FieldNotLoadedError,
    LifecycleValidationError,
    RelationNotLoadedError,
)
from action_machine.domain.hydration import build
from action_machine.domain.lifecycle import Lifecycle, StateInfo, StateType
from action_machine.domain.relation_containers import (
    AggregateMany,
    AggregateOne,
    AssociationMany,
    AssociationOne,
    BaseRelationMany,
    BaseRelationOne,
    CompositeMany,
    CompositeOne,
    RelationType,
)
from action_machine.domain.relation_markers import Inverse, NoGraphEdge, NoInverse, Rel
from action_machine.domain.testing import make
from action_machine.intents.entity.entity_intent import EntityIntent


def __getattr__(name: str) -> object:
    """
    Lazily expose graph interchange types and the ``@entity`` decorator.

    ``entity`` is not imported at package init because ``entity_decorator`` pulls
    :mod:`action_machine.domain` while :mod:`~action_machine.intents.entity` may still be
    bootstrapping. Graph interchange symbols below likewise avoid eager imports that recurse
    when :mod:`~action_machine.graph_model.nodes.domain_graph_node` loads via
    :mod:`action_machine.domain.base_domain` mid-package-init.
    """
    # pylint: disable=import-outside-toplevel

    if name == "entity":
        from action_machine.intents.entity.entity_decorator import entity

        globals()["entity"] = entity
        return entity
    if name == "DomainGraphNode":
        from action_machine.graph_model.nodes.domain_graph_node import DomainGraphNode

        globals()["DomainGraphNode"] = DomainGraphNode
        return DomainGraphNode
    if name == "DomainGraphNodeInspector":
        from action_machine.graph_model.inspectors.domain_graph_node_inspector import (
            DomainGraphNodeInspector,
        )

        globals()["DomainGraphNodeInspector"] = DomainGraphNodeInspector
        return DomainGraphNodeInspector
    if name == "EntityGraphNode":
        from action_machine.graph_model.nodes.entity_graph_node import EntityGraphNode

        globals()["EntityGraphNode"] = EntityGraphNode
        return EntityGraphNode
    if name == "EntityGraphNodeInspector":
        from action_machine.graph_model.inspectors.entity_graph_node_inspector import (
            EntityGraphNodeInspector,
        )

        globals()["EntityGraphNodeInspector"] = EntityGraphNodeInspector
        return EntityGraphNodeInspector
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "AggregateMany",
    "AggregateOne",
    "AssociationMany",
    "AssociationOne",
    # Domains
    "BaseDomain",
    # Entities
    "BaseEntity",
    "BaseRelationMany",
    # Relation containers
    "BaseRelationOne",
    "CompositeMany",
    "CompositeOne",
    "DomainGraphNode",
    "DomainGraphNodeInspector",
    # Exceptions
    "EntityDecoratorError",
    "EntityGraphNode",
    "EntityGraphNodeInspector",
    "EntityIntent",
    "FieldNotLoadedError",
    # Relation markers
    "Inverse",
    # State machines
    "Lifecycle",
    "LifecycleValidationError",
    "NoGraphEdge",
    "NoInverse",
    "Rel",
    "RelationNotLoadedError",
    "RelationType",
    "StateInfo",
    "StateType",
    # Utilities
    "build",
    "entity",
    "make",
]
