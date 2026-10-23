"""Reproduce, on the merged baseline, what a dictionary-typed field does today.

Run from the repository root:

    uv run --extra dev python specs/018-dictionary-reference/evidence/baseline_probe.py

Every block prints one measurement the specification rests on. The probe is re-run, not
re-read, whenever a phase begins.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import (
    AssociationOne,
    BaseCoreEntity,
    BaseDomain,
    BaseEnumEntity,
    BaseSpecEntity,
    NoInverse,
    NoRelation,
    value,
)
from aoa.action_machine.graph.nodes.entity_graph_node import EntityGraphNode
from aoa.action_machine.graph.validators.entity_field_validator import validate_entity_fields
from aoa.action_machine.intents.entity import entity


class ProbeDomain(BaseDomain):
    """Group the probe's declarations."""

    name = "probe"
    description = "Probe"


@entity(description="Regions the shop sells in", domain=ProbeDomain)
class RegionEnumEntity(BaseEnumEntity):
    """Declare the region vocabulary."""

    EU = value(code="eu", display_name="Europe")
    US = value(code="us", display_name="United States")


@entity(description="A structural target", domain=ProbeDomain)
class TargetCoreEntity(BaseCoreEntity):
    """Stand in for a structural entity."""

    id: str = Field(description="Identifier")


def _validate(label: str, entity_cls: type) -> None:
    """Print whether the field rule accepts one class and, when it refuses, why."""
    try:
        validate_entity_fields([entity_cls])
    except Exception as error:  # noqa: BLE001 - the probe reports the answer, whatever it is
        details = getattr(error, "details", str(error))
        print(f"{label}: REFUSED {details}")
    else:
        print(f"{label}: accepted")


@entity(description="Scalar and collection references", domain=ProbeDomain)
class OfferCoreEntity(BaseCoreEntity):
    """Reference a dictionary as a scalar and as a collection."""

    id: str = Field(description="Offer id")
    region: RegionEnumEntity = Field(description="Primary region")
    regions: tuple[RegionEnumEntity, ...] = Field(description="Regions served")


@entity(description="Optional references", domain=ProbeDomain)
class PlayerCoreEntity(BaseCoreEntity):
    """Reference a dictionary through an optional field."""

    id: str = Field(description="Player id")
    gender: RegionEnumEntity | None = Field(default=None, description="Gender")


@entity(description="Bare structural entity", domain=ProbeDomain)
class BareStructuralCoreEntity(BaseCoreEntity):
    """Show the refusal the dictionary does not get."""

    id: str = Field(description="Identifier")
    target: TargetCoreEntity = Field(description="Bare target")


@entity(description="Relation container around a dictionary", domain=ProbeDomain)
class ContainerOnEnumCoreEntity(BaseCoreEntity):
    """Show that a relation container around a dictionary is accepted today."""

    id: str = Field(description="Identifier")
    region: Annotated[AssociationOne[RegionEnumEntity], NoInverse()] = Field(description="Region relation")


@entity(description="Embedded marker on a dictionary", domain=ProbeDomain)
class MarkerOnEnumCoreEntity(BaseCoreEntity):
    """Show the refusal the embedded-value marker already gets on a dictionary."""

    id: str = Field(description="Identifier")
    region: Annotated[RegionEnumEntity, NoRelation("a value")] = Field(description="Region value")


class EmptyDictionaryEnumEntity(BaseEnumEntity):
    """Declare a dictionary with no values; ``@entity`` refuses one, so it stays undecorated."""


@entity(description="Field typed by an empty dictionary", domain=ProbeDomain)
class EmptyDictionaryCoreEntity(BaseCoreEntity):
    """Show where the empty-catalogue refusal happens today."""

    id: str = Field(description="Identifier")
    region: EmptyDictionaryEnumEntity = Field(description="Region")


@entity(description="Union of two structural entities", domain=ProbeDomain)
class UnionCoreEntity(BaseCoreEntity):
    """Show the wording a union gets today."""

    id: str = Field(description="Identifier")
    ref: TargetCoreEntity | BaseSpecEntity = Field(description="Union")


@entity(description="Heterogeneous collection", domain=ProbeDomain)
class SpecTargetSpecEntity(BaseSpecEntity):
    """Stand in for the second structural type."""

    id: str = Field(description="Identifier")


@entity(description="Heterogeneous tuple", domain=ProbeDomain)
class MixedTupleCoreEntity(BaseCoreEntity):
    """Show the wording a heterogeneous collection gets today."""

    id: str = Field(description="Identifier")
    ref: tuple[TargetCoreEntity, SpecTargetSpecEntity] = Field(description="Mixed")


@entity(description="Mapping", domain=ProbeDomain)
class MappingCoreEntity(BaseCoreEntity):
    """Show the wording a mapping gets today."""

    id: str = Field(description="Identifier")
    ref: dict[str, TargetCoreEntity] = Field(description="Mapping")


def main() -> None:
    """Print every measurement the specification rests on."""
    print("== the rule sees no dictionary ==")
    for label, entity_cls in (
        ("bare D", OfferCoreEntity),
        ("D | None", PlayerCoreEntity),
        ("container around D", ContainerOnEnumCoreEntity),
        ("bare structural", BareStructuralCoreEntity),
        ("marker on D", MarkerOnEnumCoreEntity),
    ):
        _validate(label, entity_cls)

    print("== graph rows and edges ==")
    node = EntityGraphNode(OfferCoreEntity)
    for edge in node.entity_field_edges:
        field = edge.target_node
        print(
            f"row {field.label:<8} type={field.properties['field_type']:<34} "
            f"reference_qualname={field.properties.get('reference_qualname')}"
        )
    print("edges:", sorted({edge.edge_name for edge in node.get_all_edges()}))

    print("== container around a dictionary ==")
    container = EntityGraphNode(ContainerOnEnumCoreEntity)
    print("edges:", sorted({edge.edge_name for edge in container.get_all_edges()}))
    for edge in container.get_all_edges():
        if edge.edge_name == "entity_relation":
            print("relation target:", edge.target_node_id)

    print("== empty catalogue ==")
    try:
        EntityGraphNode(EmptyDictionaryCoreEntity)
    except Exception as error:  # noqa: BLE001 - the probe reports the answer, whatever it is
        print(f"graph build: {type(error).__name__}: {error}")
    else:
        print("graph build: accepted")

    print("== refusal wording ==")
    for label, entity_cls in (
        ("union", UnionCoreEntity),
        ("heterogeneous tuple", MixedTupleCoreEntity),
        ("mapping", MappingCoreEntity),
    ):
        _validate(label, entity_cls)


if __name__ == "__main__":
    main()
