# packages/aoa-action-machine/tests/support/specialization_order/declared_late.py
"""
A head with two kinds whose kinds link to an entity declared after them (issue #415).

Importing this module must finish. ``PartCoreEntity`` comes last on purpose; its twin
``declared_first`` holds the same classes with ``PartCoreEntity`` first. The tests import
both in a fresh process, because a module run through ``exec()`` does not show the bug.
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
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.base_storage import BaseStorage


class LateOrderDomain(BaseDomain):
    """The domain of this module."""

    name = "late_order"
    description = "A part declared after the kinds"


@meta(description="Stores the late order entities", domain=LateOrderDomain)
class LateOrderStorage(BaseStorage):
    """Hold the late order entities."""


@entity(description="Kinds", resource=LateOrderStorage)
class KindEnumEntity(BaseEnumEntity):
    """The two kinds of a head."""

    VARIANT = value(code="variant", display_name="Variant")
    OTHER = value(code="other", display_name="Other")


@entity(description="Head", resource=LateOrderStorage)
class HeadCoreEntity(BaseCoreEntity):
    """The common part, with two kinds."""

    id: str = Field(description="Id")
    kind: Annotated[Specialization[VariantSpecEntity | OtherSpecEntity, KindEnumEntity], Inverse(field_name="head")] = (
        Field(description="Kind")
    )


@entity(description="Variant", resource=LateOrderStorage)
class VariantSpecEntity(BaseSpecEntity):
    """The first kind, linking to parts."""

    id: str = Field(description="Id")
    head: Annotated[
        Generalization[HeadCoreEntity], Classifier(variant=KindEnumEntity.VARIANT), Inverse(HeadCoreEntity, "kind")
    ] = Field(description="Head")
    parts: Annotated[AssociationMany[PartCoreEntity], Inverse(PartCoreEntity, "variants")] = Field(description="Parts")


@entity(description="Other variant", resource=LateOrderStorage)
class OtherSpecEntity(BaseSpecEntity):
    """The second kind, linking to parts."""

    id: str = Field(description="Id")
    head: Annotated[
        Generalization[HeadCoreEntity], Classifier(variant=KindEnumEntity.OTHER), Inverse(HeadCoreEntity, "kind")
    ] = Field(description="Head")
    parts: Annotated[AssociationMany[PartCoreEntity], Inverse(PartCoreEntity, "others")] = Field(description="Parts")


@entity(description="A part the variants link to", resource=LateOrderStorage)
class PartCoreEntity(BaseCoreEntity):
    """Declared after the kinds that link to it."""

    id: str = Field(description="Id")
    variants: Annotated[AssociationMany[VariantSpecEntity], Inverse(VariantSpecEntity, "parts")] = Field(
        description="Variants"
    )
    others: Annotated[AssociationMany[OtherSpecEntity], Inverse(OtherSpecEntity, "parts")] = Field(description="Others")


for _model in (HeadCoreEntity, VariantSpecEntity, OtherSpecEntity, PartCoreEntity):
    _model.model_rebuild()
