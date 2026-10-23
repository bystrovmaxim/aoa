# tests/action_machine/graph/test_entity_specialization_rules_axis.py
"""
The rules read on one axis, in the form the dictionary made current.

Every case declares a head whose container names a closed dictionary, and the
alternatives that either answer to it or fail to. The cases that belonged to the
classifier field are gone with the field: a classifier is no longer a field, so a
"classifier that is a relation" or "a classifier naming the axis itself" cannot be
written. What remains is the shape of the axis: the classes, their reachability,
their pairing, and the two-sided value comparison.
"""

from __future__ import annotations

from typing import Annotated

import pytest
from pydantic import Field

from aoa.action_machine.domain import (
    AssociationOne,
    BaseAssocEntity,
    BaseCoreEntity,
    BaseDomain,
    BaseEntity,
    BaseEnumEntity,
    BaseSpecEntity,
    Classifier,
    Generalization,
    Inverse,
    Rel,
    Specialization,
    value,
)
from aoa.action_machine.domain.exceptions import SpecializationDeclarationError
from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.graph.validators.entity_specialization_validator import (
    validate_entity_specializations,
)
from aoa.action_machine.intents.entity import entity


class AxisDomain(BaseDomain):
    name = "axis"
    description = "axis"


def _refuses(classes: list[type[BaseEntity]], rule: str) -> str:
    """Assert the build refuses ``classes`` with ``rule`` and return the message."""
    with pytest.raises(SpecializationDeclarationError) as caught:
        validate_entity_specializations(classes)
    message = str(caught.value)
    assert rule in message, message
    return message


@exclude_graph_model
@entity(description="Kind", domain=AxisDomain)
class _KindEnumEntity(BaseEnumEntity):
    """The dictionary most cases borrow from."""

    A = value(code="a", display_name="A")
    B = value(code="b", display_name="B")


# ─────────────────────────────────────────────────────────────────────────────
# A stranger in the union
# ─────────────────────────────────────────────────────────────────────────────


@exclude_graph_model
class StrangerAxisAssocEntity(BaseAssocEntity):
    """Shaped like an entity but never decorated, so the graph would have no node for it."""


@exclude_graph_model
@entity(description="Stranger head", domain=AxisDomain)
class StrangerHeadCoreEntity(BaseCoreEntity):
    """Names a class the walk never sees."""

    id: str = Field(description="id")
    pack: Specialization[StrangerAxisAssocEntity, _KindEnumEntity] = Rel(description="d")


StrangerHeadCoreEntity.model_rebuild()


def test_an_alternative_that_is_not_a_declared_entity_is_refused() -> None:
    message = _refuses([StrangerHeadCoreEntity], "is not a declared entity")
    assert "StrangerAxisAssocEntity" in message
    assert "@entity" in message, "the message says how to fix it"


# ─────────────────────────────────────────────────────────────────────────────
# The values, both sides
# ─────────────────────────────────────────────────────────────────────────────


@exclude_graph_model
@entity(description="Silent alternative", domain=AxisDomain)
class SilentSpecEntity(BaseSpecEntity):
    """Keeps the earlier marker form, so it names a code rather than a value."""

    id: str = Field(description="id")
    rec: Generalization[SilentHeadCoreEntity] = Rel(description="back, naming no value")


@exclude_graph_model
@entity(description="Silent head", domain=AxisDomain)
class SilentHeadCoreEntity(BaseCoreEntity):
    """One alternative answers with a code, not a value."""

    id: str = Field(description="id")
    pack: Specialization[SilentSpecEntity, _KindEnumEntity] = Rel(description="d")


SilentHeadCoreEntity.model_rebuild()
SilentSpecEntity.model_rebuild()


def test_an_alternative_that_names_no_value_is_refused() -> None:
    message = _refuses([SilentHeadCoreEntity, SilentSpecEntity], "names no value")
    assert "Classifier(field=..., variant=" in message, "the message says how to fix it"


@exclude_graph_model
@entity(description="Alpha", domain=AxisDomain)
class _AlphaSpecEntity(BaseSpecEntity):
    """Names the first value."""

    id: str = Field(description="id")
    rec: Annotated[
        Generalization[UncoveredHeadCoreEntity],
        Classifier(field="rec", variant=_KindEnumEntity.A),
    ] = Rel(description="back")


@exclude_graph_model
@entity(description="Uncovered head", domain=AxisDomain)
class UncoveredHeadCoreEntity(BaseCoreEntity):
    """Borrows two values but declares one alternative."""

    id: str = Field(description="id")
    pack: Specialization[_AlphaSpecEntity, _KindEnumEntity] = Rel(description="d")


UncoveredHeadCoreEntity.model_rebuild()
_AlphaSpecEntity.model_rebuild()


def test_a_value_with_no_alternative_is_refused() -> None:
    message = _refuses([UncoveredHeadCoreEntity, _AlphaSpecEntity], "no alternative declares them")
    assert "b" in message


# ─────────────────────────────────────────────────────────────────────────────
# The reverse field: reachable, single, and named
# ─────────────────────────────────────────────────────────────────────────────


@exclude_graph_model
@entity(description="Unreachable", domain=AxisDomain)
class UnreachableSpecEntity(BaseSpecEntity):
    """Declares no field that points back at its head."""

    id: str = Field(description="id")


@exclude_graph_model
@entity(description="Unreachable head", domain=AxisDomain)
class UnreachableHeadCoreEntity(BaseCoreEntity):
    """One alternative cannot be reached from the head's side."""

    id: str = Field(description="id")
    pack: Specialization[UnreachableSpecEntity, _KindEnumEntity] = Rel(description="d")


UnreachableHeadCoreEntity.model_rebuild()


def test_an_alternative_with_no_reverse_field_leaves_the_head_naming_a_value_nobody_owns() -> None:
    message = _refuses([UnreachableHeadCoreEntity, UnreachableSpecEntity], "no alternative declares them")
    assert "a" in message


@exclude_graph_model
@entity(description="Two way", domain=AxisDomain)
class TwoWaySpecEntity(BaseSpecEntity):
    """Points back through two fields, so the axis cannot tell which one declares its value."""

    id: str = Field(description="id")
    rec: Annotated[
        Generalization[TwoWayHeadCoreEntity],
        Classifier(field="rec", variant=_KindEnumEntity.A),
    ] = Rel(description="back")
    spare: Annotated[
        Generalization[TwoWayHeadCoreEntity],
        Classifier(field="spare", variant=_KindEnumEntity.B),
    ] = Rel(description="back again")


@exclude_graph_model
@entity(description="Two way head", domain=AxisDomain)
class TwoWayHeadCoreEntity(BaseCoreEntity):
    """The head of the two-way alternative."""

    id: str = Field(description="id")
    pack: Specialization[TwoWaySpecEntity, _KindEnumEntity] = Rel(description="d")


TwoWayHeadCoreEntity.model_rebuild()
TwoWaySpecEntity.model_rebuild()


def test_an_alternative_pointing_back_through_two_fields_is_refused() -> None:
    assert "more than one field" in _refuses([TwoWayHeadCoreEntity, TwoWaySpecEntity], "more than one field")


@exclude_graph_model
@entity(description="Wrongly paired", domain=AxisDomain)
class WronglyPairedSpecEntity(BaseSpecEntity):
    """Points back through a field the axis did not name."""

    id: str = Field(description="id")
    rec: Annotated[
        Generalization[WronglyPairedHeadCoreEntity],
        Classifier(field="rec", variant=_KindEnumEntity.A),
    ] = Rel(description="back")
    other: AssociationOne[WronglyPairedHeadCoreEntity] = Rel(
        description="a second link, so the inverse name can disagree"
    )


@exclude_graph_model
@entity(description="Wrongly paired head", domain=AxisDomain)
class WronglyPairedHeadCoreEntity(BaseCoreEntity):
    """The axis names a field the alternative does not use to point back."""

    id: str = Field(description="id")
    pack: Annotated[
        Specialization[WronglyPairedSpecEntity, _KindEnumEntity],
        Inverse(field_name="other"),
    ] = Rel(description="d")


WronglyPairedHeadCoreEntity.model_rebuild()
WronglyPairedSpecEntity.model_rebuild()


def test_an_alternative_paired_through_another_field_name_is_refused() -> None:
    message = _refuses([WronglyPairedHeadCoreEntity, WronglyPairedSpecEntity], "but the axis names")
    assert "rec" in message


# ─────────────────────────────────────────────────────────────────────────────
# The declaration that is right
# ─────────────────────────────────────────────────────────────────────────────


@exclude_graph_model
@entity(description="Good first", domain=AxisDomain)
class _GoodFirstSpecEntity(BaseSpecEntity):
    """Names the first value."""

    id: str = Field(description="id")
    rec: Annotated[
        Generalization[GoodHeadCoreEntity],
        Classifier(field="rec", variant=_KindEnumEntity.A),
        Inverse(GoodHeadCoreEntity, "pack"),
    ] = Rel(description="back")


@exclude_graph_model
@entity(description="Good second", domain=AxisDomain)
class _GoodSecondSpecEntity(BaseSpecEntity):
    """Names the second value."""

    id: str = Field(description="id")
    rec: Annotated[
        Generalization[GoodHeadCoreEntity],
        Classifier(field="rec", variant=_KindEnumEntity.B),
        Inverse(GoodHeadCoreEntity, "pack"),
    ] = Rel(description="back")


@exclude_graph_model
@entity(description="Good head", domain=AxisDomain)
class GoodHeadCoreEntity(BaseCoreEntity):
    """Every value the dictionary declares has exactly one alternative."""

    id: str = Field(description="id")
    pack: Annotated[
        Specialization[_GoodFirstSpecEntity | _GoodSecondSpecEntity, _KindEnumEntity],
        Inverse(field_name="rec"),
    ] = Rel(description="d")


GoodHeadCoreEntity.model_rebuild()
_GoodFirstSpecEntity.model_rebuild()
_GoodSecondSpecEntity.model_rebuild()


def test_a_correct_declaration_passes() -> None:
    validate_entity_specializations(
        [GoodHeadCoreEntity, _GoodFirstSpecEntity, _GoodSecondSpecEntity, _KindEnumEntity]
    )


def test_a_model_without_any_specialization_passes() -> None:
    validate_entity_specializations([])
