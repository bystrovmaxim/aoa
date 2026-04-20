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
PACKAGE CONTENTS
═══════════════════════════════════════════════════════════════════════════════

Domains:
    BaseDomain — abstract base for all domain marker classes.
    DomainGraphNode — interchange node for a concrete ``BaseDomain`` class (see :mod:`action_machine.domain.graph_model`).

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

"""

from action_machine.domain.base_domain import BaseDomain
from action_machine.domain.entity import BaseEntity
from action_machine.domain.graph_model import (
    DomainGraphNode,
    DomainGraphNodeInspector,
    EntityGraphNode,
    EntityGraphNodeInspector,
)
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
from action_machine.intents.entity.entity_decorator import entity
from action_machine.legacy.entity_intent import EntityIntent

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
