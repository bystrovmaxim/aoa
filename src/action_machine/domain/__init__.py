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
         │ at coordinator.build()
         v
    EntityIntentInspector  ──reads scratch + model_fields──>  FacetVertex / snapshots
         │
         v
    GraphCoordinator graph  (entity nodes, belongs_to domain, relation edges, …)

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- This package exports only domain-layer contracts and helpers.
- Entity declarations are validated through the shared ``GraphCoordinator`` graph.
- Entities, actions, and other facets coexist in one graph (no separate entity coordinator).
- ``entity`` decorator and ``EntityIntent`` marker must be used together for graph participation.

═══════════════════════════════════════════════════════════════════════════════
PACKAGE CONTENTS
═══════════════════════════════════════════════════════════════════════════════

Domains:
    BaseDomain — abstract base for all domain marker classes.
    DomainNode — interchange node for a concrete ``BaseDomain`` class (id, label, meta).

Entities:
    BaseEntity — abstract base for all entities (frozen, `extra="forbid"`).
    EntityIntent — marker mixin: the type declares participation in the
    ``@entity`` grammar (facet / inspector at ``GraphCoordinator.build()``).
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

    from action_machine.runtime.machines.core import Core
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

    # Built coordinator includes entity inspector; entities appear in the graph:
    coordinator = Core.create_coordinator()

    order = build({"id": "123", "amount": 100.0}, OrderEntity)

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Transport/storage behavior is intentionally outside this package.
- Graph validation requires registering relevant inspectors before coordinator ``build()``.
- Runtime field/relation access may raise domain exceptions for unloaded data.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Public API surface for ActionMachine domain modeling.
CONTRACT: Export domain/entity/relation/lifecycle building blocks and hydration utilities.
INVARIANTS: Domain facets integrate through shared coordinator graph, not a separate pipeline.
FLOW: declaration via markers/decorators -> inspector extraction -> coordinator graph/snapshots -> runtime hydration/access.
FAILURES: domain declaration and runtime access errors are surfaced via exported domain exceptions.
EXTENSION POINTS: applications define custom domains/entities/lifecycles and relation topology.
AI-CORE-END
"""

from action_machine.domain.base_domain import BaseDomain
from action_machine.domain.entity import BaseEntity
from action_machine.intents.domain.domain_node import DomainNode
from action_machine.intents.domain.entity_decorator import entity
from action_machine.intents.domain.entity_intent import EntityIntent
from action_machine.intents.domain.entity_node import EntityNode
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

__all__ = [
    "AggregateMany",
    "AggregateOne",
    "AssociationMany",
    "AssociationOne",
    # Domains
    "BaseDomain",
    "DomainNode",
    "EntityNode",
    # Entities
    "BaseEntity",
    "BaseRelationMany",
    # Relation containers
    "BaseRelationOne",
    "CompositeMany",
    "CompositeOne",
    # Exceptions
    "EntityDecoratorError",
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
