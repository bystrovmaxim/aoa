"""Reproduce a specialization reverse inverse paired with a NoInverse head.
Run: .venv/bin/python docs/reports/evidence/specialization_direction.py
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
    NoInverse,
    Specialization,
    value,
)
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine


class DirectionDomain(BaseDomain):
    """Group the specialization reproduction."""

    name = "specialization_direction"
    description = "Specialization direction reproduction"


@entity(description="Kinds", domain=DirectionDomain)
class KindEnumEntity(BaseEnumEntity):
    """Provide one classified alternative."""

    ONLY = value(code="only", display_name="Only")


@entity(description="Head", domain=DirectionDomain)
class HeadCoreEntity(BaseCoreEntity):
    """Declare the head endpoint without an inverse."""

    detail: Annotated[Specialization[DetailSpecEntity, KindEnumEntity], NoInverse()] = Field(description="Detail")


@entity(description="Alternative", domain=DirectionDomain)
class DetailSpecEntity(BaseSpecEntity):
    """Declare an inverse that points at the unpaired head."""

    head: Annotated[
        Generalization[HeadCoreEntity], Classifier(variant=KindEnumEntity.ONLY), Inverse(field_name="detail")
    ] = Field(description="Head")


def main() -> None:
    """Build the public machine with the inconsistent pair."""
    HeadCoreEntity.model_rebuild()
    DetailSpecEntity.model_rebuild()
    ActionProductMachine(loggers=[])
    print("Generalization Inverse paired with Specialization NoInverse: accepted (defect)")


if __name__ == "__main__":
    main()
