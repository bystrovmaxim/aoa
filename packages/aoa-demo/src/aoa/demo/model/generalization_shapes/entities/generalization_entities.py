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

    GeneralizationHeadEntity
        └── details: Specialization[A | B]        → entity_specialization axis
    GeneralizationVariantAEntity.head: Generalization[Head]  → parent_entity edge
    GeneralizationVariantBEntity.head: Generalization[Head]  → parent_entity edge
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from aoa.action_machine.domain import (
    BaseEntity,
    Classifier,
    Generalization,
    Inverse,
    Rel,
    Specialization,
)
from aoa.action_machine.intents.entity import entity

from aoa.demo.model.generalization_shapes.generalization_shapes_domain import GeneralizationShapesDomain


@entity(
    description="Shape: the specialization head — its axis and the two extensions draw the ERD generalization",
    domain=GeneralizationShapesDomain,
)
class GeneralizationHeadEntity(BaseEntity):
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
        Specialization[GeneralizationVariantAEntity | GeneralizationVariantBEntity],
        Classifier(field="variant_code", codes=Literal["variant_a", "variant_b"]),
        Inverse(field_name="head"),
    ] = Rel(
        description="Shape: the specialization axis — one of the declared variants"
    )  # type: ignore[assignment]


@entity(
    description="Shape: an extension entity — the ERD draws a parent_entity arrow into the head",
    domain=GeneralizationShapesDomain,
)
class GeneralizationVariantAEntity(BaseEntity):
    """
    AI-CORE-BEGIN
    ROLE: Drawing fixture extension; its reverse field is the drawn inheritance edge.
    CONTRACT: One ``Generalization`` field declaring the head and this variant's code.
    INVARIANTS: No business meaning; the inheritance is the shape being drawn.
    AI-CORE-END
    """

    id: str = Field(description="Variant A row id")

    head: Annotated[
        Generalization[GeneralizationHeadEntity],
        Classifier("head", Literal["variant_a"]),
    ] = Rel(
        description="Shape: the extension's reverse field — the parent_entity edge into the head"
    )  # type: ignore[assignment]


@entity(
    description="Shape: a second extension entity — the ERD draws another parent_entity arrow into the head",
    domain=GeneralizationShapesDomain,
)
class GeneralizationVariantBEntity(BaseEntity):
    """
    AI-CORE-BEGIN
    ROLE: Drawing fixture extension; its reverse field is the drawn inheritance edge.
    CONTRACT: One ``Generalization`` field declaring the head and this variant's code.
    INVARIANTS: No business meaning; the inheritance is the shape being drawn.
    AI-CORE-END
    """

    id: str = Field(description="Variant B row id")

    head: Annotated[
        Generalization[GeneralizationHeadEntity],
        Classifier("head", Literal["variant_b"]),
    ] = Rel(
        description="Shape: the extension's reverse field — the parent_entity edge into the head"
    )  # type: ignore[assignment]


GeneralizationHeadEntity.model_rebuild()
GeneralizationVariantAEntity.model_rebuild()
GeneralizationVariantBEntity.model_rebuild()
