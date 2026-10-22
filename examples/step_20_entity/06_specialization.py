"""Describe one variant of the same object.

A counterparty has common information. Its organisation variant adds a registration number. Both describe the same counterparty and use its identifier.

Run: uv run python examples/step_20_entity/06_specialization.py
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from aoa.action_machine.domain import (
    BaseCoreEntity,
    BaseSpecEntity,
    Classifier,
    Generalization,
    Inverse,
    Rel,
    Specialization,
)
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine


class ShopDomain(BaseDomain):
    """Group the shop model declarations."""

    name = "shop"
    description = "Shop model"


@entity(description="Counterparty", domain=ShopDomain)
class CounterpartyCoreEntity(BaseCoreEntity):
    """Hold the common identity and the selected counterparty kind."""

    id: str = Field(description="Counterparty identifier")
    kind: str = Field(description="Counterparty variant code")
    details: Annotated[
        Specialization[OrganisationSpecEntity],
        Classifier(field="kind", codes=Literal["organisation"]),
        Inverse(field_name="counterparty"),
    ] = Rel(description="Variant-specific data")


@entity(description="Organisation data of a counterparty", domain=ShopDomain)
class OrganisationSpecEntity(BaseSpecEntity):
    """Add organisation data to the same counterparty."""

    id: str = Field(description="The head counterparty identifier")
    registration: str = Field(description="Organisation registration number")
    counterparty: Annotated[
        Generalization[CounterpartyCoreEntity],
        Classifier("counterparty", Literal["organisation"]),
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
    id="party-1", kind="organisation",
    details=Specialization[OrganisationSpecEntity](id="party-1", variant="organisation", entity=details),
)
assert party.id == details.id == details.counterparty.id
print("same identity:", party.id == details.id)
print("registration:", party.details.entity.registration)
