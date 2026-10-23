"""Describe one variant of the same object.

A counterparty has common information. Its organisation variant adds a registration number. Both describe the same counterparty and use its identifier.

Run: uv run python examples/step_20_entity/06_specialization.py
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import (
    BaseCoreEntity,
    BaseEnumEntity,
    BaseSpecEntity,
    Classifier,
    Generalization,
    Inverse,
    Rel,
    Specialization,
    value,
)
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine


class ShopDomain(BaseDomain):
    """Group the shop model declarations."""

    name = "shop"
    description = "Shop model"


@entity(description="Kind of CounterpartyCoreEntity", domain=ShopDomain)
class CounterpartyKindEnumEntity(BaseEnumEntity):
    """Declare the codes the axis borrows."""

    ORGANISATION = value(code="organisation", display_name="Organisation")


@entity(description="Counterparty", domain=ShopDomain)
class CounterpartyCoreEntity(BaseCoreEntity):
    """Hold the common identity and the selected counterparty kind."""

    id: str = Field(description="Counterparty identifier")
    details: Annotated[
        Specialization[OrganisationSpecEntity, CounterpartyKindEnumEntity],
        Inverse(field_name="counterparty"),
    ] = Rel(description="Variant-specific data")


@entity(description="Organisation data of a counterparty", domain=ShopDomain)
class OrganisationSpecEntity(BaseSpecEntity):
    """Add organisation data to the same counterparty."""

    id: str = Field(description="The head counterparty identifier")
    registration: str = Field(description="Organisation registration number")
    counterparty: Annotated[
        Generalization[CounterpartyCoreEntity],
        Classifier(field="counterparty", variant=CounterpartyKindEnumEntity.ORGANISATION),
        Inverse(CounterpartyCoreEntity, "details"),
    ] = Rel(description="Common counterparty data")


CounterpartyCoreEntity.model_rebuild()
OrganisationSpecEntity.model_rebuild()

ActionProductMachine(loggers=[])

details = OrganisationSpecEntity(
    id="party-1", registration="REG-42",
    counterparty=Generalization[CounterpartyCoreEntity](id="party-1"),
)
party = CounterpartyCoreEntity(
    id="party-1",
    details=Specialization[OrganisationSpecEntity, CounterpartyKindEnumEntity](
        id="party-1", variant=CounterpartyKindEnumEntity.ORGANISATION, entity=details
    ),
)
assert party.id == details.id == details.counterparty.id
print("same identity:", party.id == details.id)
print("registration:", party.details.entity.registration)
