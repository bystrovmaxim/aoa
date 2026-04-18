# tests/scenarios/domain_model/entities.py
"""
Test entities for the domain model.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Defines test entities used to exercise domain features:
BaseEntity, the @entity decorator, Lifecycle, relations, and GraphCoordinator.

═══════════════════════════════════════════════════════════════════════════════
ENTITIES
═══════════════════════════════════════════════════════════════════════════════

- SampleEntity — simple entity with no relations or lifecycle.
- LifecycleEntity — entity with a lifecycle (DraftLifecycle).
- RelatedEntity — entity with relations.
- ComplexEntity — entity combining the above.

═══════════════════════════════════════════════════════════════════════════════
SPECIALIZED LIFECYCLE CLASSES
═══════════════════════════════════════════════════════════════════════════════

DraftLifecycle — three-state machine: draft → active → archived.
Used by LifecycleEntity and ComplexEntity.

_template is defined at class definition time (import-time).
At startup, GraphCoordinator finds DraftLifecycle in model_fields,
reads _template, and validates eight lifecycle integrity rules.

Each entity instance holds its own current state:
    entity.lifecycle.current_state       → "draft"
    entity.lifecycle.can_transition("active")  → True
    entity.lifecycle.available_transitions     → {"active"}

State transition (frozen entity):
    new_lc = entity.lifecycle.transition("active")
    updated = entity.model_copy(update={"lifecycle": new_lc})

═══════════════════════════════════════════════════════════════════════════════
USAGE IN TESTS
═══════════════════════════════════════════════════════════════════════════════

These entities are used in unit tests to verify:

- Correct construction via @entity
- Metadata assembly via ``GraphCoordinator.build()`` and ``get_snapshot``
- Lifecycle validation (eight integrity rules)
- Relations (Annotated + Inverse/NoInverse + Rel)
- build() and make() behavior
- Specialized Lifecycle helpers (current_state, transition)
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import (
    AggregateMany,
    AssociationOne,
    BaseEntity,
    Lifecycle,
    NoInverse,
    Rel,
    entity,
)
from action_machine.domain.base_domain import BaseDomain

# ═══════════════════════════════════════════════════════════════════════════════
# DOMAIN
# ═══════════════════════════════════════════════════════════════════════════════


class TestDomain(BaseDomain):
    """Test domain marker for exercising domain machinery."""

    name = "test"
    description = "Test domain"


# ═══════════════════════════════════════════════════════════════════════════════
# SPECIALIZED LIFECYCLE CLASSES
# ═══════════════════════════════════════════════════════════════════════════════


class DraftLifecycle(Lifecycle):
    """
    Three-state machine: draft → active → archived.

    _template is created at import-time. GraphCoordinator validates
    eight integrity rules at application startup.
    """

    _template = (
        Lifecycle()
        .state("draft", "Draft").to("active").initial()
        .state("active", "Active").to("archived").intermediate()
        .state("archived", "Archived").final()
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ENTITIES
# ═══════════════════════════════════════════════════════════════════════════════


@entity(description="Simple test entity", domain=TestDomain)
class SampleEntity(BaseEntity):
    """Minimal entity for basic tests. No relations or lifecycle."""

    id: str = Field(description="Identifier")
    name: str = Field(description="Name")
    value: int = Field(description="Value", ge=0)


@entity(description="Entity with lifecycle", domain=TestDomain)
class LifecycleEntity(BaseEntity):
    """
    Entity for lifecycle tests.

    lifecycle is a normal Pydantic field (DraftLifecycle | None).
    Each instance holds its own current state:

        entity = LifecycleEntity(id="1", lifecycle=DraftLifecycle("draft"))
        entity.lifecycle.current_state  # → "draft"

    Without lifecycle:
        entity = LifecycleEntity(id="1", lifecycle=None)
        entity.lifecycle  # → None

    Partial load:
        entity = LifecycleEntity.partial(id="1")
        entity.lifecycle  # → FieldNotLoadedError
    """

    id: str = Field(description="Identifier")
    lifecycle: DraftLifecycle | None = Field(description="Lifecycle state machine")


@entity(description="Related entity", domain=TestDomain)
class RelatedEntity(BaseEntity):
    """
    Entity for relation tests.

    parent — optional self-association (no Inverse).
    children — aggregate collection to self (no Inverse).
    """

    id: str = Field(description="Identifier")
    title: str = Field(description="Title")

    parent: Annotated[
        AssociationOne[RelatedEntity] | None,
        NoInverse(),
    ] = Rel(description="Parent entity")

    children: Annotated[
        AggregateMany[RelatedEntity] | None,
        NoInverse(),
    ] = Rel(description="Child entities")


@entity(description="Complex entity", domain=TestDomain)
class ComplexEntity(BaseEntity):
    """
    Full-featured entity for integration-style tests.

    Includes:
    - Scalar fields (id, name, amount).
    - Lifecycle (DraftLifecycle).
    - AssociationOne to LifecycleEntity (no Inverse).
    - AggregateMany to RelatedEntity (no Inverse).
    """

    id: str = Field(description="Identifier")
    name: str = Field(description="Name")
    amount: float = Field(description="Amount", ge=0)

    lifecycle: DraftLifecycle | None = Field(description="Lifecycle state machine")

    owner: Annotated[
        AssociationOne[LifecycleEntity] | None,
        NoInverse(),
    ] = Rel(description="Owner")

    related_items: Annotated[
        AggregateMany[RelatedEntity] | None,
        NoInverse(),
    ] = Rel(description="Related items")
