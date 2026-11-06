"""Use complete relationship fields on Core, Assoc, Detail and Spec hosts.
Run: .venv/bin/python examples/step_24_relations/66_complete_stereotypes.py
"""

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import (
    AggregateMany,
    AssociationMany,
    AssociationOne,
    BaseAssocEntity,
    BaseCoreEntity,
    BaseDetailEntity,
    BaseEnumEntity,
    BaseSpecEntity,
    CompositeOne,
    NoInverse,
    value,
)
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.graph.validators.entity_field_validator import validate_entity_fields
from aoa.action_machine.graph.validators.entity_inverse_validator import validate_entity_inverses
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.base_storage import BaseStorage
from aoa.action_machine.resources import InMemoryDataSource


class KindDomain(BaseDomain):
    """Group the relationship kinds."""

    name = "kinds"
    description = "Complete relationship fields"


@meta(description="Where KindStorage keeps its rows")
class KindDataSource(InMemoryDataSource):
    """The store KindStorage works with."""


@meta(description="Stores the kind entities", domain=KindDomain)
class KindStorage(BaseStorage[KindDataSource]):
    """Hold the kind entities."""


@entity(description="Region catalogue", resource=KindStorage)
class RegionEnumEntity(BaseEnumEntity):
    """Provide a shared selection target."""

    EU = value(code="eu", display_name="Europe")


@entity(description="Offer", resource=KindStorage)
class OfferCoreEntity(BaseCoreEntity):
    """Select a dictionary value from a Core host."""

    region: Annotated[AssociationOne[RegionEnumEntity], NoInverse()] = Field(description="Sales region")


@entity(description="Technical offer link", resource=KindStorage)
class OfferAssocEntity(BaseAssocEntity):
    """Link technical endpoints with explicit directions."""

    offer: Annotated[AssociationOne[OfferCoreEntity], NoInverse()] = Field(description="Linked offer")
    related: Annotated[AssociationMany[OfferCoreEntity], NoInverse()] = Field(description="Other offers")


@entity(description="Offer detail", resource=KindStorage)
class OfferDetailEntity(BaseDetailEntity):
    """Name the owner through an association."""

    owner: Annotated[AssociationOne[OfferCoreEntity], NoInverse()] = Field(description="Owning offer")


@entity(description="Offer variant data", resource=KindStorage)
class OfferSpecEntity(BaseSpecEntity):
    """Use ordinary links alongside variant-specific data."""

    related: Annotated[AggregateMany[OfferCoreEntity], NoInverse()] = Field(description="Related offers")
    detail: Annotated[CompositeOne[OfferDetailEntity] | None, NoInverse()] = Field(
        default=None, description="Extra detail"
    )


def main() -> None:
    """Validate each host and construct its relation values."""
    validate_entity_fields([OfferCoreEntity, OfferAssocEntity, OfferDetailEntity, OfferSpecEntity])
    validate_entity_inverses([OfferCoreEntity, OfferAssocEntity, OfferDetailEntity, OfferSpecEntity])
    core = OfferCoreEntity(region=AssociationOne(id="eu"))
    assoc = OfferAssocEntity(offer=AssociationOne(id="offer-1"), related=AssociationMany(ids=("offer-2",)))
    detail = OfferDetailEntity(owner=AssociationOne(id="offer-1"))
    spec = OfferSpecEntity(related=AggregateMany(ids=("offer-2",)))
    assert core.region.entity is RegionEnumEntity.EU
    assert assoc.offer.id == detail.owner.id == "offer-1"
    assert spec.detail is None and spec.related.ids == ("offer-2",)
    print("Core: eu; Assoc: offer-1; Detail: offer-1; Spec: nullable detail")


if __name__ == "__main__":
    main()
