# packages/aoa-action-machine/src/aoa/action_machine/domain/__init__.py
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
intents: ``intent -> decorator -> scratch -> inspector -> coordinator``.

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

Entities:
    BaseEntity — abstract base for all entities (frozen, `extra="forbid"`).
    EntityIntent — marker mixin: the type declares participation in the
    ``@entity`` grammar (graph-node inspectors at ``NodeGraphCoordinator.build()``).
    The six kind markers — ``BaseCoreEntity`` (an independent object),
    ``BaseAssocEntity`` (a technical link), ``BaseDetailEntity`` (an owner's part),
    ``BaseSpecEntity`` (variant data of the same object), ``BaseEnumEntity``
    (a shared reference value) and ``BaseStateEntity`` (a lifecycle state).

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

    from aoa.action_machine.domain import (
        AssociationOne,
        BaseDomain,
        BaseCoreEntity,
        BaseStateEntity,
        CompositeMany,
        Inverse,
        Lifecycle,
        Rel,
        build,
    )

    class ShopDomain(BaseDomain):
        name = "shop"
        description = "E-commerce shop bounded context"

    class OrderStateEntity(BaseStateEntity):
        sort_order: int = Field(default=0, description="Presentation order")

        NEW = OrderStateEntity(code="new", display_name="New", sort_order=1)
        DONE = OrderStateEntity(code="done", display_name="Done", sort_order=2)

    class OrderLifecycle(Lifecycle):
        _template = (
            Lifecycle()
            .state(OrderStateEntity.NEW).to(OrderStateEntity.DONE).initial()
            .state(OrderStateEntity.DONE).final()
        )

    @entity(description="Customer order", domain=ShopDomain)
    class OrderCoreEntity(BaseCoreEntity):
        id: str = Field(description="Order identifier")
        amount: float = Field(description="Order total", ge=0)
        lifecycle: OrderLifecycle = Field(description="Order status axis")

    order = build({"id": "123", "amount": 100.0}, OrderCoreEntity)
"""

from aoa.action_machine.domain.assoc_entity import BaseAssocEntity
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.domain.core_entity import BaseCoreEntity
from aoa.action_machine.domain.detail_entity import BaseDetailEntity
from aoa.action_machine.domain.entity import BaseEntity
from aoa.action_machine.domain.entity_schema_marker import EntitySchemaMarker, entity_schema_marker_from_annotated
from aoa.action_machine.domain.enum_entity import BaseEnumEntity
from aoa.action_machine.domain.exceptions import (
    EntityDecoratorError,
    FieldNotLoadedError,
    ForeignStateError,
    LifecycleGraphError,
    LifecycleValidationError,
    MissingStateError,
    RelationNotLoadedError,
    SpecializationDeclarationError,
)
from aoa.action_machine.domain.hydration import build
from aoa.action_machine.domain.lifecycle import Lifecycle, StateInfo, StateType
from aoa.action_machine.domain.relation_containers import (
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
from aoa.action_machine.domain.relation_markers import (
    Inverse,
    NoGraphEdge,
    NoInverse,
    Rel,
)
from aoa.action_machine.domain.spec_entity import BaseSpecEntity
from aoa.action_machine.domain.specialization_containers import Classifier, Generalization, Specialization
from aoa.action_machine.domain.state_entity import BaseStateEntity
from aoa.action_machine.domain.testing import make
from aoa.action_machine.intents.entity.entity_intent import EntityIntent

__all__ = [
    "AggregateMany",
    "AggregateOne",
    "AssociationMany",
    "AssociationOne",
    # Domains, entities and the six kind markers
    "BaseAssocEntity",
    "BaseCoreEntity",
    "BaseDetailEntity",
    "BaseDomain",
    "BaseEntity",
    "BaseEnumEntity",
    "BaseRelationMany",
    "BaseRelationOne",
    "BaseSpecEntity",
    "BaseStateEntity",
    "Classifier",
    "CompositeMany",
    "CompositeOne",
    # Exceptions
    "EntityDecoratorError",
    "EntityIntent",
    "EntitySchemaMarker",
    "FieldNotLoadedError",
    "ForeignStateError",
    # Relation markers
    "Generalization",
    "Inverse",
    # State machines
    "Lifecycle",
    "LifecycleGraphError",
    "LifecycleValidationError",
    "MissingStateError",
    "NoGraphEdge",
    "NoInverse",
    "Rel",
    "RelationNotLoadedError",
    "RelationType",
    "Specialization",
    "SpecializationDeclarationError",
    "StateInfo",
    "StateType",
    # Utilities
    "build",
    "entity_schema_marker_from_annotated",
    "make",
]
