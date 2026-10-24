"""Distinguish independent NoInverse links from reciprocal endpoint pairs.
Run: .venv/bin/python examples/step_21_relations/73_role_directions.py
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import (
    AggregateOne,
    AssociationMany,
    AssociationOne,
    BaseCoreEntity,
    BaseDomain,
    CompositeMany,
    EntityFieldDeclarationError,
    Inverse,
    NoInverse,
)
from aoa.action_machine.graph.nodes.entity_graph_node import EntityGraphNode
from aoa.action_machine.intents.entity import entity


class DirectionDomain(BaseDomain):
    """Group independent and reciprocal relationship declarations."""

    name = "role-directions"
    description = "Relationship directions"


@entity(description="Independent first object", domain=DirectionDomain)
class FirstCoreEntity(BaseCoreEntity):
    """Declare one link without claiming a reciprocal endpoint."""

    second: Annotated[CompositeMany[SecondCoreEntity], NoInverse()] = Field(description="Independent second links")


@entity(description="Independent second object", domain=DirectionDomain)
class SecondCoreEntity(BaseCoreEntity):
    """Declare a different unpaired relationship back to the first type."""

    first: Annotated[AggregateOne[FirstCoreEntity], NoInverse()] = Field(description="Independent first link")


@entity(description="Single bookmark", domain=DirectionDomain)
class BookmarkCoreEntity(BaseCoreEntity):
    """Use NoInverse without any reverse declaration."""

    target: Annotated[AssociationOne[FirstCoreEntity], NoInverse()] = Field(description="Bookmarked object")


@entity(description="Paired owner", domain=DirectionDomain)
class OwnerCoreEntity(BaseCoreEntity):
    """Name an explicit reciprocal endpoint."""

    entries: Annotated[AssociationMany[ItemCoreEntity], Inverse(field_name="owner")] = Field(
        description="Related items"
    )


@entity(description="Paired item", domain=DirectionDomain)
class ItemCoreEntity(BaseCoreEntity):
    """Name the owner endpoint back."""

    owner: Annotated[AssociationOne[OwnerCoreEntity], Inverse(field_name="entries")] = Field(
        description="Related owner"
    )


@entity(description="Unpaired reverse", domain=DirectionDomain)
class UnpairedCoreEntity(BaseCoreEntity):
    """Remain unpaired even when another field points at this type."""

    source: Annotated[AssociationOne[SourceCoreEntity], NoInverse()] = Field(description="Unpaired source")


@entity(description="Incorrectly paired source", domain=DirectionDomain)
class SourceCoreEntity(BaseCoreEntity):
    """Try to use an unpaired field as the reverse endpoint."""

    target: Annotated[AssociationOne[UnpairedCoreEntity], Inverse(field_name="source")] = Field(description="Target")


for model in (FirstCoreEntity, SecondCoreEntity, OwnerCoreEntity, ItemCoreEntity, UnpairedCoreEntity, SourceCoreEntity):
    model.model_rebuild()


def independent_links() -> None:
    """Keep two opposite-direction NoInverse fields as separate edges."""
    first = EntityGraphNode(FirstCoreEntity)
    second = EntityGraphNode(SecondCoreEntity)
    assert len(first.relations) == len(second.relations) == 1
    assert first.relations[0].properties["relation_type"] == "composition"
    assert second.relations[0].properties["relation_type"] == "aggregation"
    assert not first.relations[0].properties["has_inverse"]
    assert not second.relations[0].properties["has_inverse"]
    assert "inverse_field" not in first.relations[0].properties
    assert "inverse_field" not in second.relations[0].properties
    assert not EntityGraphNode(BookmarkCoreEntity).relations[0].properties["has_inverse"]
    print("Single NoInverse: accepted")
    print("Two NoInverse fields: two independent links, no reciprocal pair")


def reciprocal_links() -> None:
    """Validate reciprocal markers and preserve their reverse metadata."""
    owner = EntityGraphNode(OwnerCoreEntity)
    item = EntityGraphNode(ItemCoreEntity)
    assert owner.relations[0].properties["has_inverse"]
    assert item.relations[0].properties["has_inverse"]
    assert owner.relations[0].properties["inverse_field"] == "owner"
    assert item.relations[0].properties["inverse_field"] == "entries"
    print("Two reciprocal Inverse fields: accepted")


def conflicting_directions() -> None:
    """Refuse an Inverse that names a NoInverse field."""
    try:
        EntityGraphNode(SourceCoreEntity)
    except EntityFieldDeclarationError as error:
        assert (
            str(error)
            == "Field 'target' on entity 'SourceCoreEntity' is invalid: the reverse field 'source' on UnpairedCoreEntity declares no Inverse (it is NoInverse or missing a direction marker); declare a reciprocal Inverse(...) on both endpoints."
        )
        assert error.field_name == "target"
        print(type(error).__name__ + ": " + str(error))
    else:
        raise AssertionError("Inverse pointing at NoInverse was accepted")


def main() -> None:
    """Run independent links, a valid pair and the conflicting direction."""
    independent_links()
    reciprocal_links()
    conflicting_directions()


if __name__ == "__main__":
    main()
