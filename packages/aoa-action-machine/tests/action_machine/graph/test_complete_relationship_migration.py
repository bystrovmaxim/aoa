# tests/action_machine/graph/test_complete_relationship_migration.py
"""
Before/after migration regressions for the intentional breaking changes.

Each formerly accepted form — a bare dictionary, a NoRelation embedded value and a one-sided
inverse — is refused with an actionable correction, while its complete replacement passes.
"""

from __future__ import annotations

import textwrap

from ...support.isolated_entity_models import run_isolated_model

_IMPORTS = textwrap.dedent(
    """
    from typing import Annotated

    from pydantic import Field

    from aoa.action_machine.domain import (
        AssociationMany,
        AssociationOne,
        BaseCoreEntity,
        BaseDomain,
        BaseEnumEntity,
        Inverse,
        NoInverse,
        NoRelation,
        value,
    )
    from aoa.action_machine.domain.exceptions import EntityFieldDeclarationError
    from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
    from aoa.action_machine.graph.validators.entity_field_validator import validate_entity_fields
    from aoa.action_machine.graph.validators.entity_inverse_validator import validate_entity_inverses
    from aoa.action_machine.intents.entity import entity


    class MigrationDomain(BaseDomain):
        name = "migration"
        description = "Migration"
    """
)


def _run(body: str) -> str:
    result = run_isolated_model(_IMPORTS + "\n" + textwrap.dedent(body))
    assert result.returncode == 0, result.stderr
    return result.stdout


def test_a_bare_dictionary_migrates_to_an_explicit_association() -> None:
    """The bare dictionary form is refused; the AssociationOne[D] replacement passes."""
    out = _run(
        """
        @entity(description="Currency", domain=MigrationDomain)
        class CurrencyEnumEntity(BaseEnumEntity):
            EUR = value(code="eur", display_name="Euro")

        @exclude_graph_model
        @entity(description="Bare", domain=MigrationDomain)
        class BareCoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")
            currency: CurrencyEnumEntity = Field(description="Currency")

        @exclude_graph_model
        @entity(description="Complete", domain=MigrationDomain)
        class CompleteCoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")
            currency: Annotated[AssociationOne[CurrencyEnumEntity], NoInverse()] = Field(description="Currency")

        try:
            validate_entity_fields([BareCoreEntity])
            print("BARE_ACCEPT")
        except EntityFieldDeclarationError as exc:
            print("BARE_REFUSE " + exc.field_name + " " + str("AssociationOne" in exc.details))

        validate_entity_fields([CompleteCoreEntity])
        print("COMPLETE_ACCEPT")
        """
    )

    assert "BARE_REFUSE currency True" in out
    assert "COMPLETE_ACCEPT" in out


def test_no_relation_migrates_to_a_complete_relationship() -> None:
    """The NoRelation embedded value is refused; a complete relationship passes."""
    out = _run(
        """
        @exclude_graph_model
        @entity(description="Target", domain=MigrationDomain)
        class TargetCoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")

        @exclude_graph_model
        @entity(description="Embedded", domain=MigrationDomain)
        class EmbeddedCoreEntity(BaseCoreEntity):
            value: Annotated[TargetCoreEntity, NoRelation("embedded snapshot")] = Field(description="Value")

        @exclude_graph_model
        @entity(description="Complete", domain=MigrationDomain)
        class CompleteRelationCoreEntity(BaseCoreEntity):
            target: Annotated[AssociationOne[TargetCoreEntity], NoInverse()] = Field(description="Target")

        try:
            validate_entity_fields([EmbeddedCoreEntity])
            print("EMBED_ACCEPT")
        except EntityFieldDeclarationError as exc:
            print("EMBED_REFUSE " + exc.field_name + " " + str("NoRelation" in exc.details))

        validate_entity_fields([CompleteRelationCoreEntity])
        print("COMPLETE_ACCEPT")
        """
    )

    assert "EMBED_REFUSE value True" in out
    assert "COMPLETE_ACCEPT" in out


def test_a_one_sided_inverse_migrates_to_reciprocal_markers() -> None:
    """A one-sided inverse is refused; the reciprocal pair passes."""
    out = _run(
        """
        @exclude_graph_model
        @entity(description="One-sided offer", domain=MigrationDomain)
        class OfferCoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")
            regions: Annotated[AssociationMany[RegionCoreEntity], NoInverse()] = Field(description="Regions")

        @exclude_graph_model
        @entity(description="One-sided region", domain=MigrationDomain)
        class RegionCoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")
            offer: Annotated[AssociationOne[OfferCoreEntity], Inverse(field_name="regions")] = Field(description="Offer")

        OfferCoreEntity.model_rebuild()
        RegionCoreEntity.model_rebuild()

        try:
            validate_entity_inverses([RegionCoreEntity, OfferCoreEntity])
            print("ONE_SIDED_ACCEPT")
        except EntityFieldDeclarationError as exc:
            print("ONE_SIDED_REFUSE " + exc.entity_name + " " + exc.field_name)

        @exclude_graph_model
        @entity(description="Reciprocal offer", domain=MigrationDomain)
        class ReciprocalOfferCoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")
            regions: Annotated[AssociationMany[ReciprocalRegionCoreEntity], Inverse(field_name="offer")] = Field(
                description="Regions"
            )

        @exclude_graph_model
        @entity(description="Reciprocal region", domain=MigrationDomain)
        class ReciprocalRegionCoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")
            offer: Annotated[AssociationOne[ReciprocalOfferCoreEntity], Inverse(field_name="regions")] = Field(
                description="Offer"
            )

        ReciprocalOfferCoreEntity.model_rebuild()
        ReciprocalRegionCoreEntity.model_rebuild()
        validate_entity_inverses([ReciprocalRegionCoreEntity, ReciprocalOfferCoreEntity])
        print("RECIPROCAL_ACCEPT")
        """
    )

    assert "ONE_SIDED_REFUSE RegionCoreEntity offer" in out
    assert "RECIPROCAL_ACCEPT" in out
