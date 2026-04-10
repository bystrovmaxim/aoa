"""
Domain package — bounded-context model for ActionMachine (entities, domains, relations, lifecycles).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

This package holds a **declarative** domain model: entities, fields, relations
between entities, and lifecycle state machines — and intentionally **nothing**
about databases, HTTP, files, or other adapters. That is the “pure domain”
center in a hexagonal sense: the same `OrderEntity` can be loaded from Postgres,
Mongo, a REST API, or a test double; persistence belongs to resource managers,
not to the entity type itself.

═══════════════════════════════════════════════════════════════════════════════
HOW THIS FITS THE AOA GRAMMAR (GATE HOST → DECORATOR → SCRATCH → INSPECTOR → COORDINATOR)
═══════════════════════════════════════════════════════════════════════════════

**Gate host** — a marker mixin on a class: “this type is allowed to use a
specific slice of the AOA grammar.” Decorators and validators use
`issubclass(cls, SomeGateHost)` so intent is explicit and invariants have a
stable anchor.

**Decorator** — the **grammar of business intent** at import time: it writes
**scratch** (class-level attributes such as `_entity_info`) that describe what
was declared.

**Scratch** — the class’s **self-description** of which grammar was applied
(attributes and helpers such as `BaseEntity.partial`, relation containers, etc.).
Reads are local and fast; they do not require traversing the coordinator graph.

**Inspector** — a class **paired with** gate hosts: discovers relevant subclasses,
reads scratch / model structure, emits `FacetPayload` nodes (and optional typed
facet snapshots) for the coordinator.

**Gate coordinator** — after `register(...).build()`, holds the **system-wide**
facet graph (`rustworkx`) and facet snapshots: checks **acyclicity** of
structural edges and **consistency** of all declared intentions together.
Entities participate in the **same** graph as Actions and other facets when
`EntityGateHostInspector` is registered on that coordinator.

    @entity  ──writes──>  _entity_info  (scratch)
         │
         │ requires
         v
    EntityGateHost  (marker: “this class may use @entity”)
         │
         │ at coordinator.build()
         v
    EntityGateHostInspector  ──reads scratch + model_fields──>  FacetPayload / snapshots
         │
         v
    GateCoordinator graph  (entity nodes, belongs_to domain, relation edges, …)

═══════════════════════════════════════════════════════════════════════════════
COORDINATOR
═══════════════════════════════════════════════════════════════════════════════

The shared entry point for the **built** metadata graph is `GateCoordinator`
(`action_machine.metadata.gate_coordinator`). Entity facets are not a separate
“mini coordinator”: they are **nodes and payloads in the same graph** as Actions,
plugins, resource managers, etc., once the appropriate inspectors are
registered and `build()` has completed.

═══════════════════════════════════════════════════════════════════════════════
PACKAGE CONTENTS
═══════════════════════════════════════════════════════════════════════════════

Domains:
    BaseDomain — abstract base for all domain marker classes.

Entities:
    BaseEntity — abstract base for all entities (frozen, `extra="forbid"`).
    EntityGateHost — marker mixin that authorizes `@entity`.
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
USAGE SKETCH
═══════════════════════════════════════════════════════════════════════════════

    from pydantic import Field

    from action_machine.core.core_action_machine import CoreActionMachine
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

    # Built coordinator includes entity inspector — entities appear in the graph:
    coordinator = CoreActionMachine.create_coordinator()

    order = build({"id": "123", "amount": 100.0}, OrderEntity)
"""

from .base_domain import BaseDomain
from .entity import BaseEntity
from .entity_decorator import entity
from .entity_gate_host import EntityGateHost
from .exceptions import (
    EntityDecoratorError,
    FieldNotLoadedError,
    LifecycleValidationError,
    RelationNotLoadedError,
)
from .hydration import build
from .lifecycle import Lifecycle, StateInfo, StateType
from .relation_containers import (
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
from .relation_markers import Inverse, NoInverse, Rel
from .testing import make

__all__ = [
    # Domains
    "BaseDomain",
    # Entities
    "BaseEntity",
    "EntityGateHost",
    "entity",
    # State machines
    "Lifecycle",
    "StateType",
    "StateInfo",
    # Relation containers
    "BaseRelationOne",
    "BaseRelationMany",
    "CompositeOne",
    "CompositeMany",
    "AggregateOne",
    "AggregateMany",
    "AssociationOne",
    "AssociationMany",
    "RelationType",
    # Relation markers
    "Inverse",
    "NoInverse",
    "Rel",
    # Utilities
    "build",
    "make",
    # Exceptions
    "EntityDecoratorError",
    "FieldNotLoadedError",
    "LifecycleValidationError",
    "RelationNotLoadedError",
]
