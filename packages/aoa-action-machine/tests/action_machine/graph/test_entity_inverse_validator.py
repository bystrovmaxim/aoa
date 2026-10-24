# tests/action_machine/graph/test_entity_inverse_validator.py
"""
Tests for ``validate_entity_inverses`` — every paired relation declares its reciprocal.

Both endpoints of a mutual pair name each other through ``Inverse``; a one-sided inverse,
an ``Inverse`` paired with ``NoInverse``, a missing or wrong reverse field, a concrete-target
mismatch and a non-reciprocal pair are refused. Each declaration is built in a fresh
interpreter so it never joins the shared model.
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
        Inverse,
        NoInverse,
    )
    from aoa.action_machine.domain.exceptions import EntityFieldDeclarationError
    from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
    from aoa.action_machine.graph.validators.entity_inverse_validator import validate_entity_inverses
    from aoa.action_machine.intents.entity import entity


    class InvDomain(BaseDomain):
        name = "inv"
        description = "Inverse"


    def probe(*classes):
        try:
            validate_entity_inverses(list(classes))
            print("ACCEPT")
        except EntityFieldDeclarationError as exc:
            print("REFUSE " + exc.entity_name + " " + exc.field_name + " :: " + exc.details)
    """
)


def _run(body: str) -> str:
    result = run_isolated_model(_IMPORTS + "\n" + textwrap.dedent(body))
    assert result.returncode == 0, result.stderr
    return result.stdout


_RECIPROCAL = """
    @exclude_graph_model
    @entity(description="Region", domain=InvDomain)
    class RegionCoreEntity(BaseCoreEntity):
        id: str = Field(description="Identifier")
        offer: Annotated[AssociationOne[OfferCoreEntity], Inverse(field_name="regions")] = Field(description="Offer")

    @exclude_graph_model
    @entity(description="Offer", domain=InvDomain)
    class OfferCoreEntity(BaseCoreEntity):
        id: str = Field(description="Identifier")
        regions: Annotated[AssociationMany[RegionCoreEntity], Inverse(field_name="offer")] = Field(description="Regions")

    RegionCoreEntity.model_rebuild()
    OfferCoreEntity.model_rebuild()
    probe(RegionCoreEntity, OfferCoreEntity)
"""


def test_a_reciprocal_field_only_pair_passes() -> None:
    """Both endpoints resolve their field-only inverse from the container target."""
    out = _run(_RECIPROCAL)

    assert "ACCEPT" in out


def test_a_reciprocal_concrete_class_pair_passes() -> None:
    """Both endpoints name the concrete target class and the reverse field."""
    out = _run(
        """
        @exclude_graph_model
        @entity(description="Region", domain=InvDomain)
        class RegionCoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")
            offer: Annotated[AssociationOne[OfferCoreEntity], Inverse(OfferCoreEntity, "regions")] = Field(
                description="Offer"
            )

        @exclude_graph_model
        @entity(description="Offer", domain=InvDomain)
        class OfferCoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")
            regions: Annotated[AssociationMany[RegionCoreEntity], Inverse(RegionCoreEntity, "offer")] = Field(
                description="Regions"
            )

        RegionCoreEntity.model_rebuild()
        OfferCoreEntity.model_rebuild()
        probe(RegionCoreEntity, OfferCoreEntity)
        """
    )

    assert "ACCEPT" in out


def test_a_one_sided_inverse_is_refused() -> None:
    """A field declaring Inverse with a NoInverse reverse endpoint is a breaking migration."""
    out = _run(
        """
        @exclude_graph_model
        @entity(description="Offer", domain=InvDomain)
        class OfferCoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")
            regions: Annotated[AssociationMany[RegionCoreEntity], NoInverse()] = Field(description="Regions")

        @exclude_graph_model
        @entity(description="Region", domain=InvDomain)
        class RegionCoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")
            offer: Annotated[AssociationOne[OfferCoreEntity], Inverse(field_name="regions")] = Field(description="Offer")

        probe(RegionCoreEntity)
        """
    )

    assert "REFUSE RegionCoreEntity offer" in out


def test_a_missing_reverse_field_is_refused() -> None:
    """An inverse naming a field that does not exist is refused."""
    out = _run(
        """
        @exclude_graph_model
        @entity(description="Offer", domain=InvDomain)
        class OfferCoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")

        @exclude_graph_model
        @entity(description="Region", domain=InvDomain)
        class RegionCoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")
            offer: Annotated[AssociationOne[OfferCoreEntity], Inverse(field_name="regions")] = Field(description="Offer")

        probe(RegionCoreEntity)
        """
    )

    assert "REFUSE RegionCoreEntity offer" in out
    assert "does not exist" in out


def test_a_wrong_reverse_field_is_refused() -> None:
    """A reverse field that points back to a different field is refused."""
    out = _run(
        """
        @exclude_graph_model
        @entity(description="Offer", domain=InvDomain)
        class OfferCoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")
            regions: Annotated[AssociationMany[RegionCoreEntity], Inverse(field_name="other")] = Field(
                description="Regions"
            )

        @exclude_graph_model
        @entity(description="Region", domain=InvDomain)
        class RegionCoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")
            offer: Annotated[AssociationOne[OfferCoreEntity], Inverse(field_name="regions")] = Field(description="Offer")
            other: Annotated[AssociationOne[OfferCoreEntity], NoInverse()] = Field(description="Other")

        probe(RegionCoreEntity, OfferCoreEntity)
        """
    )

    assert "REFUSE" in out


def test_a_concrete_target_mismatch_is_refused() -> None:
    """A concrete Inverse target that is not the resolved container target is refused."""
    out = _run(
        """
        @exclude_graph_model
        @entity(description="Offer", domain=InvDomain)
        class OfferCoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")
            regions: Annotated[AssociationMany[RegionCoreEntity], Inverse(field_name="offer")] = Field(
                description="Regions"
            )

        @exclude_graph_model
        @entity(description="Other", domain=InvDomain)
        class OtherCoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")

        @exclude_graph_model
        @entity(description="Region", domain=InvDomain)
        class RegionCoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")
            offer: Annotated[AssociationOne[OfferCoreEntity], Inverse(OtherCoreEntity, "regions")] = Field(
                description="Offer"
            )

        probe(RegionCoreEntity)
        """
    )

    assert "REFUSE RegionCoreEntity offer" in out
    assert "does not match" in out


def test_no_inverse_one_way_pair_passes() -> None:
    """NoInverse on both sides is a valid intentionally unpaired declaration."""
    out = _run(
        """
        @exclude_graph_model
        @entity(description="Offer", domain=InvDomain)
        class OfferCoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")

        @exclude_graph_model
        @entity(description="Region", domain=InvDomain)
        class RegionCoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")
            offer: Annotated[AssociationOne[OfferCoreEntity], NoInverse()] = Field(description="Offer")

        probe(RegionCoreEntity)
        """
    )

    assert "ACCEPT" in out


def test_unchanged_inherited_field_keeps_the_base_endpoint() -> None:
    """An unchanged inherited field reuses its base declaring owner for reciprocity."""
    out = _run(
        """
        @exclude_graph_model
        @entity(description="Item", domain=InvDomain)
        class ItemCoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")
            owner: Annotated[AssociationOne[BaseHostCoreEntity], Inverse(field_name="items")] = Field(
                description="Owner"
            )

        @exclude_graph_model
        @entity(description="Base host", domain=InvDomain)
        class BaseHostCoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")
            items: Annotated[AssociationMany[ItemCoreEntity], Inverse(field_name="owner")] = Field(description="Items")

        @exclude_graph_model
        @entity(description="Child host", domain=InvDomain)
        class ChildHostCoreEntity(BaseHostCoreEntity):
            extra: str = Field(description="Extra")

        ItemCoreEntity.model_rebuild()
        BaseHostCoreEntity.model_rebuild()
        probe(BaseHostCoreEntity, ItemCoreEntity, ChildHostCoreEntity)
        """
    )

    assert "ACCEPT" in out


def test_an_override_pointing_at_the_base_pair_is_refused() -> None:
    """An override must declare its own reciprocal endpoint, not reuse the base pair."""
    out = _run(
        """
        @exclude_graph_model
        @entity(description="Item", domain=InvDomain)
        class ItemCoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")
            owner: Annotated[AssociationOne[BaseHostCoreEntity], Inverse(field_name="items")] = Field(
                description="Owner"
            )

        @exclude_graph_model
        @entity(description="Base host", domain=InvDomain)
        class BaseHostCoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")
            items: Annotated[AssociationMany[ItemCoreEntity], Inverse(field_name="owner")] = Field(description="Items")

        @exclude_graph_model
        @entity(description="Child host", domain=InvDomain)
        class ChildHostCoreEntity(BaseHostCoreEntity):
            items: Annotated[AssociationMany[ItemCoreEntity], Inverse(field_name="owner")] = Field(description="Items")

        probe(ChildHostCoreEntity, ItemCoreEntity)
        """
    )

    assert "REFUSE" in out


def test_a_grandchild_inheriting_a_valid_override_passes() -> None:
    """A grandchild that inherits a valid override reuses that override's endpoint."""
    out = _run(
        """
        @exclude_graph_model
        @entity(description="Item", domain=InvDomain)
        class ItemCoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")
            owner: Annotated[AssociationOne[ChildHostCoreEntity], Inverse(field_name="items")] = Field(
                description="Owner"
            )

        @exclude_graph_model
        @entity(description="Child host", domain=InvDomain)
        class ChildHostCoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")
            items: Annotated[AssociationMany[ItemCoreEntity], Inverse(field_name="owner")] = Field(description="Items")

        @exclude_graph_model
        @entity(description="Grandchild host", domain=InvDomain)
        class GrandchildHostCoreEntity(ChildHostCoreEntity):
            extra: str = Field(description="Extra")

        ItemCoreEntity.model_rebuild()
        ChildHostCoreEntity.model_rebuild()
        probe(ChildHostCoreEntity, ItemCoreEntity, GrandchildHostCoreEntity)
        """
    )

    assert "ACCEPT" in out
