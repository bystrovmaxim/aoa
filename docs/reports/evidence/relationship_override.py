"""Reproduce an explicit override accepted as its inherited endpoint.
Run: .venv/bin/python docs/reports/evidence/relationship_override.py
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationMany, AssociationOne, BaseCoreEntity, Inverse
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.graph.validators.entity_field_validator import validate_entity_fields
from aoa.action_machine.graph.validators.entity_inverse_validator import validate_entity_inverses
from aoa.action_machine.intents.entity import entity


class OverrideDomain(BaseDomain):
    """Group the override reproduction."""

    name = "override"
    description = "Override reproduction"


@entity(description="Item", domain=OverrideDomain)
class ItemCoreEntity(BaseCoreEntity):
    """Point at the base host."""

    owner: Annotated[AssociationOne[BaseHostCoreEntity], Inverse(field_name="entries")] = Field(description="Owner")


@entity(description="Base host", domain=OverrideDomain)
class BaseHostCoreEntity(BaseCoreEntity):
    """Introduce the original endpoint."""

    entries: Annotated[AssociationMany[ItemCoreEntity], Inverse(field_name="owner")] = Field(description="Items")


@entity(description="Unchanged child", domain=OverrideDomain)
class UnchangedHostCoreEntity(BaseHostCoreEntity):
    """Inherit the endpoint without redeclaring it."""


@entity(description="Override child", domain=OverrideDomain)
class OverrideHostCoreEntity(BaseHostCoreEntity):
    """Redeclare the same annotation as a new endpoint."""

    entries: Annotated[AssociationMany[ItemCoreEntity], Inverse(field_name="owner")] = Field(description="Items")


def main() -> None:
    """Resolve every model before checking endpoint identity."""
    for model in (ItemCoreEntity, BaseHostCoreEntity, UnchangedHostCoreEntity, OverrideHostCoreEntity):
        model.model_rebuild()
    validate_entity_fields([BaseHostCoreEntity, ItemCoreEntity, UnchangedHostCoreEntity, OverrideHostCoreEntity])
    validate_entity_inverses([BaseHostCoreEntity, ItemCoreEntity, UnchangedHostCoreEntity])
    print("Unchanged inherited endpoint: accepted (expected)")
    validate_entity_inverses([BaseHostCoreEntity, ItemCoreEntity, OverrideHostCoreEntity])
    print("Explicit same-signature override: accepted (defect)")


if __name__ == "__main__":
    main()
