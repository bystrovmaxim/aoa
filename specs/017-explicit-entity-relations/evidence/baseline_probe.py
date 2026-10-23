"""
Reproduce, at the current HEAD, the four defects the specification records.

Run from the repository root:

    uv run --extra dev python specs/017-explicit-entity-relations/evidence/baseline_probe.py

Each block prints the answer the baseline gives; `research.md` carries the same
output verbatim. A block that stops reproducing is a block whose phase has begun.
"""
from enum import Enum
from typing import Annotated

from pydantic import Field, field_validator
from aoa.action_machine.domain import (
    AssociationOne, BaseCoreEntity, BaseEnumEntity, NoInverse, Rel, value,
)

print("== bare entity field ==")
class ShowcaseCoreEntity(BaseCoreEntity):
    """A showcase."""
    id: str

class PlayerCoreEntity(BaseCoreEntity):
    """A player."""
    id: str = Field(description="Player identifier")
    showcase: ShowcaseCoreEntity = Field(description="Player showcase")

print("model_fields:", list(PlayerCoreEntity.model_fields))

print("== mutable member ==")
class LabelsEnumEntity(BaseEnumEntity):
    """Declare labels shared by all users of this value."""
    labels: tuple[str, ...]
    ITEM = value(code="item", display_name="Item", labels=("original",))

    @field_validator("labels", mode="after")
    @classmethod
    def replace_with_list(cls, labels: tuple[str, ...]) -> list[str]:
        """Return a list, violating the property contract."""
        return list(labels)

LabelsEnumEntity.ITEM.labels.append("changed")
print("member:", type(LabelsEnumEntity.ITEM.labels).__name__, LabelsEnumEntity.by_code("item").labels)

print("== exported shape mismatch ==")
class ShapeEnumEntity(BaseEnumEntity):
    """Declare a tuple property."""
    labels: tuple[str, ...]
    ITEM = value(code="item", display_name="Item", labels=("a",))

    @field_validator("labels", mode="after")
    @classmethod
    def to_string(cls, labels: tuple[str, ...]) -> str:
        """Return a different immutable type."""
        return ",".join(labels)

print("member:", type(ShapeEnumEntity.ITEM.labels).__name__, ShapeEnumEntity.ITEM.to_reference())

print("== enum serialization schema ==")
class Grade(Enum):
    """Name the supported grades."""
    A = "a"

class RatedEnumEntity(BaseEnumEntity):
    """Describe a value with an enum property."""
    grade: Grade
    ITEM = value(code="item", display_name="Item", grade=Grade.A)

print("reference:", RatedEnumEntity.ITEM.to_reference())
try:
    RatedEnumEntity.model_json_schema(mode="serialization")
    print("schema: ok")
except KeyError as error:
    print("schema: KeyError", error)

print("== relation description in the default slot ==")
class TargetCoreEntity(BaseCoreEntity):
    """Identify the related object."""
    id: str

class ViaRelCoreEntity(BaseCoreEntity):
    """Demonstrate the description leaking into an instance."""
    target: Annotated[AssociationOne[TargetCoreEntity], NoInverse()] = Rel(description="Related target")

class ViaFieldCoreEntity(BaseCoreEntity):
    """Keep documentation separate from the runtime value."""
    target: Annotated[AssociationOne[TargetCoreEntity], NoInverse()] = Field(description="Related target")

print("Rel required:", ViaRelCoreEntity.model_fields["target"].is_required())
print("Field required:", ViaFieldCoreEntity.model_fields["target"].is_required())
print("omitted value type:", type(ViaRelCoreEntity().target).__name__)
