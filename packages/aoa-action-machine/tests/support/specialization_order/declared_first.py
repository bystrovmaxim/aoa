# packages/aoa-action-machine/tests/support/specialization_order/declared_first.py
"""
The classes of ``declared_late`` with ``PartCoreEntity`` declared before the kinds (issue #415).

This order loads before and after the fix of issue #415; it is the twin that shows the
order of classes is what the bug depends on.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import (
    AssociationMany,
    BaseCoreEntity,
    BaseDomain,
    BaseEnumEntity,
    BaseSpecEntity,
    Classifier,
    Generalization,
    Inverse,
    Specialization,
    value,
)
from aoa.action_machine.intents.entity import entity


class FirstOrderDomain(BaseDomain):
    """The domain of this module."""

    name = "first_order"
    description = "A part declared before the kinds"


@entity(description="A part the variants link to", domain=FirstOrderDomain)
class PartCoreEntity(BaseCoreEntity):
    """Declared before the kinds that link to it."""

    id: str = Field(description="Id")
    variants: Annotated[AssociationMany[VariantSpecEntity], Inverse(VariantSpecEntity, "parts")] = Field(
        description="Variants"
    )
    others: Annotated[AssociationMany[OtherSpecEntity], Inverse(OtherSpecEntity, "parts")] = Field(description="Others")


@entity(description="Kinds", domain=FirstOrderDomain)
class KindEnumEntity(BaseEnumEntity):
    """The two kinds of a head."""

    VARIANT = value(code="variant", display_name="Variant")
    OTHER = value(code="other", display_name="Other")


@entity(description="Head", domain=FirstOrderDomain)
class HeadCoreEntity(BaseCoreEntity):
    """The common part, with two kinds."""

    id: str = Field(description="Id")
    kind: Annotated[Specialization[VariantSpecEntity | OtherSpecEntity, KindEnumEntity], Inverse(field_name="head")] = (
        Field(description="Kind")
    )


@entity(description="Variant", domain=FirstOrderDomain)
class VariantSpecEntity(BaseSpecEntity):
    """The first kind, linking to parts."""

    id: str = Field(description="Id")
    head: Annotated[
        Generalization[HeadCoreEntity], Classifier(variant=KindEnumEntity.VARIANT), Inverse(HeadCoreEntity, "kind")
    ] = Field(description="Head")
    parts: Annotated[AssociationMany[PartCoreEntity], Inverse(PartCoreEntity, "variants")] = Field(description="Parts")


@entity(description="Other variant", domain=FirstOrderDomain)
class OtherSpecEntity(BaseSpecEntity):
    """The second kind, linking to parts."""

    id: str = Field(description="Id")
    head: Annotated[
        Generalization[HeadCoreEntity], Classifier(variant=KindEnumEntity.OTHER), Inverse(HeadCoreEntity, "kind")
    ] = Field(description="Head")
    parts: Annotated[AssociationMany[PartCoreEntity], Inverse(PartCoreEntity, "others")] = Field(description="Parts")


for _model in (HeadCoreEntity, VariantSpecEntity, OtherSpecEntity, PartCoreEntity):
    _model.model_rebuild()
