# packages/aoa-demo/src/aoa/demo/model/generalization_shapes/entities/generalization_entities.py
"""
Generalization entity fixtures — a specialization head with two extensions.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The head declares the specialization axis and the two extensions point back at
it. The framework turns the pair into the two generalization shapes the ERD
draws: the ``entity_specialization`` axis from the head into its variants, and
one ``parent_entity`` inheritance edge from each extension into the head. None
of the names is a business concept.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    GeneralizationHeadCoreEntity
        └── details: Specialization[A | B]        → entity_specialization axis
        └── replay_ticket: AssociationOne[ReplayTicket]        → messaging domain
    GeneralizationVariantASpecEntity.head: Generalization[Head]  → parent_entity edge
        └── touch_moment: AssociationOne[TouchMoment]         → catalog domain
        └── bin_coordinate: AssociationOne[BinCoordinate]     → inventory domain
    GeneralizationVariantBSpecEntity.head: Generalization[Head]  → parent_entity edge
        └── audit_log: AssociationOne[AuditLogEntry]          → store domain
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from aoa.action_machine.domain import (
    AssociationOne,
    BaseCoreEntity,
    BaseSpecEntity,
    Classifier,
    Generalization,
    Inverse,
    NoInverse,
    Rel,
    Specialization,
)
from aoa.action_machine.intents.entity import entity
from aoa.demo.model.catalog.entities.catalog_touch_moment import TouchMomentCoreEntity
from aoa.demo.model.generalization_shapes.generalization_shapes_domain import GeneralizationShapesDomain
from aoa.demo.model.inventory.entities.inv_bin_coordinate_stub import BinCoordinateStubCoreEntity
from aoa.demo.model.messaging.entities.msg_replay_ticket import ReplayTicketCoreEntity
from aoa.demo.model.store.entities.audit_log_entry import AuditLogEntryDetailEntity


@entity(
    description="Shape: the specialization head — its axis and the two extensions draw the ERD generalization",
    domain=GeneralizationShapesDomain,
)
class GeneralizationHeadCoreEntity(BaseCoreEntity):
    """
    AI-CORE-BEGIN
    ROLE: Drawing fixture head; its declared axis is one generalization shape.
    CONTRACT: One ``Specialization`` field with its classifier and inverse declared.
    INVARIANTS: No business meaning; the axis is the shape being drawn.
    AI-CORE-END
    """

    id: str = Field(description="Head row id")
    variant_code: str = Field(description="Classifier field selecting the variant for a row")

    details: Annotated[
        Specialization[GeneralizationVariantASpecEntity | GeneralizationVariantBSpecEntity],
        Classifier(field="variant_code", codes=Literal["variant_a", "variant_b"]),
        Inverse(field_name="head"),
    ] = Rel(
        description="Shape: the specialization axis — one of the declared variants"
    )  # type: ignore[assignment]

    replay_ticket: Annotated[
        AssociationOne[ReplayTicketCoreEntity],
        NoInverse(),
    ] = Rel(
        description="Shape: a plain relation from the head into the messaging domain"
    )  # type: ignore[assignment]


@entity(
    description="Shape: an extension entity — the ERD draws a parent_entity arrow into the head",
    domain=GeneralizationShapesDomain,
)
class GeneralizationVariantASpecEntity(BaseSpecEntity):
    """
    AI-CORE-BEGIN
    ROLE: Drawing fixture extension; its reverse field is the drawn inheritance edge.
    CONTRACT: One ``Generalization`` field declaring the head and this variant's code.
    INVARIANTS: No business meaning; the inheritance is the shape being drawn.
    AI-CORE-END
    """

    id: str = Field(description="Variant A row id")

    head: Annotated[
        Generalization[GeneralizationHeadCoreEntity],
        Classifier("head", Literal["variant_a"]),
    ] = Rel(
        description="Shape: the extension's reverse field — the parent_entity edge into the head"
    )  # type: ignore[assignment]

    touch_moment: Annotated[
        AssociationOne[TouchMomentCoreEntity],
        NoInverse(),
    ] = Rel(
        description="Shape: a direct relation from variant A into the catalog domain"
    )  # type: ignore[assignment]

    bin_coordinate: Annotated[
        AssociationOne[BinCoordinateStubCoreEntity],
        NoInverse(),
    ] = Rel(
        description="Shape: a direct relation from variant A into the inventory domain"
    )  # type: ignore[assignment]


@entity(
    description="Shape: a second extension entity — the ERD draws another parent_entity arrow into the head",
    domain=GeneralizationShapesDomain,
)
class GeneralizationVariantBSpecEntity(BaseSpecEntity):
    """
    AI-CORE-BEGIN
    ROLE: Drawing fixture extension; its reverse field is the drawn inheritance edge.
    CONTRACT: One ``Generalization`` field declaring the head and this variant's code.
    INVARIANTS: No business meaning; the inheritance is the shape being drawn.
    AI-CORE-END
    """

    id: str = Field(description="Variant B row id")

    head: Annotated[
        Generalization[GeneralizationHeadCoreEntity],
        Classifier("head", Literal["variant_b"]),
    ] = Rel(
        description="Shape: the extension's reverse field — the parent_entity edge into the head"
    )  # type: ignore[assignment]

    audit_log: Annotated[
        AssociationOne[AuditLogEntryDetailEntity],
        NoInverse(),
    ] = Rel(
        description="Shape: a direct relation from variant B into the store domain"
    )  # type: ignore[assignment]


GeneralizationHeadCoreEntity.model_rebuild()
GeneralizationVariantASpecEntity.model_rebuild()
GeneralizationVariantBSpecEntity.model_rebuild()
