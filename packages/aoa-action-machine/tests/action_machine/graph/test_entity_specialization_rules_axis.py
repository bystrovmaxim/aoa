# tests/action_machine/graph/test_entity_specialization_rules_axis.py
"""
The rules a specialization must satisfy **on one head**: what an axis alone can decide.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Each test builds one broken declaration and asserts the build refuses it with the named
rule. The models carry no other defect, so the error this test expects is the only error
the model can produce — which is what makes the assertion mean something: a validator
that reported something else, or reported first whatever it happened to look at, would
fail here.

The rules of this file are the ones read on a single axis: what the alternatives are,
which codes they declare, what the classifier field may be, and how the two sides of the
code comparison line up. Rules that need every axis at once live in the global file
beside this one.

═══════════════════════════════════════════════════════════════════════════════
WHAT EACH FIXTURE IS FOR
═══════════════════════════════════════════════════════════════════════════════

Every fixture is marked ``@exclude_graph_model`` because it is deliberately broken: the
validator walks the loaded entities, so a fixture left in the model would fail the build
of every other test that assembles one. Each test passes its class **explicitly**, which
is also how the exclusion stays honest — the class is not part of the model, but it is
still judged when a test asks for it.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- **SpecializationDeclarationError** — the rule named in each test.

Does not cover what pydantic refuses on its own (a class outside the union, a value of
the wrong type), which the container tests already pin.
"""

from __future__ import annotations

from typing import Annotated, Literal

import pytest
from pydantic import Field

from aoa.action_machine.domain import (
    AssociationOne,
    BaseEntity,
    Classifier,
    Generalization,
    Inverse,
    NoInverse,
    Rel,
    Specialization,
)
from aoa.action_machine.domain.base_domain import BaseDomain
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


# ─────────────────────────────────────────────────────────────────────────────
# A stranger in the union
# ─────────────────────────────────────────────────────────────────────────────


@exclude_graph_model
class StrangerAxisEntity(BaseEntity):
    """Shaped like an entity but never decorated, so the graph would have no node for it."""

    id: str = Field(description="id")


@exclude_graph_model
@entity(description="Stranger head", domain=AxisDomain)
class StrangerHeadEntity(BaseEntity):
    id: str = Field(description="id")
    media: str = Field(description="classifier")
    pack: Annotated[
        Specialization[StrangerAxisEntity], Classifier(field="media", codes=Literal["a"]), Inverse(field_name="rec")
    ] = Rel(description="d")


StrangerHeadEntity.model_rebuild()


def test_an_alternative_that_is_not_a_declared_entity_is_refused() -> None:
    message = _refuses([StrangerHeadEntity], "is not a declared entity")
    assert "StrangerAxisEntity" in message
    assert "@entity" in message, "the message says how to fix it"


# ─────────────────────────────────────────────────────────────────────────────
# The codes, both sides
# ─────────────────────────────────────────────────────────────────────────────


@exclude_graph_model
@entity(description="Silent alternative", domain=AxisDomain)
class SilentAlternativeEntity(BaseEntity):
    id: str = Field(description="id")
    rec: Annotated[Generalization[SilentHeadEntity], Inverse(SilentHeadEntity, "pack")] = Rel(description="no code")


@exclude_graph_model
@entity(description="Silent head", domain=AxisDomain)
class SilentHeadEntity(BaseEntity):
    id: str = Field(description="id")
    media: str = Field(description="classifier")
    pack: Annotated[
        Specialization[SilentAlternativeEntity],
        Classifier(field="media", codes=Literal["a"]),
        Inverse(field_name="rec"),
    ] = Rel(description="d")


SilentAlternativeEntity.model_rebuild()
SilentHeadEntity.model_rebuild()


def test_an_alternative_that_declares_no_code_is_refused() -> None:
    message = _refuses([SilentHeadEntity], "declares no code")
    assert "SilentAlternativeEntity" in message
    assert "rec" in message, "the message names the field that should carry the code"


@exclude_graph_model
@entity(description="Mismatched alternative", domain=AxisDomain)
class MismatchedAlternativeEntity(BaseEntity):
    id: str = Field(description="id")
    rec: Annotated[
        Generalization[MismatchedHeadEntity], Classifier("rec", Literal["other"]), Inverse(MismatchedHeadEntity, "pack")
    ] = Rel(description="d")


@exclude_graph_model
@entity(description="Mismatched head", domain=AxisDomain)
class MismatchedHeadEntity(BaseEntity):
    id: str = Field(description="id")
    media: str = Field(description="classifier")
    pack: Annotated[
        Specialization[MismatchedAlternativeEntity],
        Classifier(field="media", codes=Literal["mine"]),
        Inverse(field_name="rec"),
    ] = Rel(description="d")


MismatchedAlternativeEntity.model_rebuild()
MismatchedHeadEntity.model_rebuild()


def test_a_code_the_head_names_and_no_class_declares_is_refused() -> None:
    message = _refuses([MismatchedHeadEntity], "no alternative declares them")
    assert "mine" in message, "the message names the code that leads nowhere"
    assert "other" not in message, "the error is about the head's side of the comparison"


@exclude_graph_model
@entity(description="Extra alternative", domain=AxisDomain)
class ExtraCodeAlternativeEntity(BaseEntity):
    id: str = Field(description="id")
    rec: Annotated[
        Generalization[ExtraCodeHeadEntity], Classifier("rec", Literal["a"]), Inverse(ExtraCodeHeadEntity, "pack")
    ] = Rel(description="d")


@exclude_graph_model
@entity(description="Extra code head", domain=AxisDomain)
class ExtraCodeHeadEntity(BaseEntity):
    id: str = Field(description="id")
    media: str = Field(description="classifier")
    pack: Annotated[
        Specialization[ExtraCodeAlternativeEntity],
        Classifier(field="media", codes=Literal["a", "b"]),
        Inverse(field_name="rec"),
    ] = Rel(description="d")


ExtraCodeAlternativeEntity.model_rebuild()
ExtraCodeHeadEntity.model_rebuild()


def test_a_code_that_leads_nowhere_is_named_before_the_size_is_compared() -> None:
    """Two codes for one class: the head names a code no alternative answers to, and that is the report."""
    message = _refuses([ExtraCodeHeadEntity], "no alternative declares them")
    assert "'b'" in message


# ─────────────────────────────────────────────────────────────────────────────
# The classifier field
# ─────────────────────────────────────────────────────────────────────────────


@exclude_graph_model
@entity(description="Integer alternative", domain=AxisDomain)
class IntegerAlternativeEntity(BaseEntity):
    id: str = Field(description="id")
    rec: Annotated[
        Generalization[IntegerHeadEntity], Classifier("rec", Literal["a"]), Inverse(IntegerHeadEntity, "pack")
    ] = Rel(description="d")


@exclude_graph_model
@entity(description="Integer head", domain=AxisDomain)
class IntegerHeadEntity(BaseEntity):
    id: str = Field(description="id")
    media: int = Field(description="a numeric classifier cannot hold a word")
    pack: Annotated[
        Specialization[IntegerAlternativeEntity],
        Classifier(field="media", codes=Literal["a"]),
        Inverse(field_name="rec"),
    ] = Rel(description="d")


IntegerAlternativeEntity.model_rebuild()
IntegerHeadEntity.model_rebuild()


def test_a_code_the_classifier_type_cannot_hold_is_refused() -> None:
    message = _refuses([IntegerHeadEntity], "cannot be stored by classifier field")
    assert "'media'" in message
    assert "int" in message, "the message names the type that refused the code"


@exclude_graph_model
@entity(description="Relation-classified alternative", domain=AxisDomain)
class RelationClassifiedAlternativeEntity(BaseEntity):
    id: str = Field(description="id")
    rec: Annotated[
        Generalization[RelationClassifiedHeadEntity],
        Classifier("rec", Literal["a"]),
        Inverse(RelationClassifiedHeadEntity, "pack"),
    ] = Rel(description="d")


@exclude_graph_model
@entity(description="Other side", domain=AxisDomain)
class RelationClassifiedOtherEntity(BaseEntity):
    id: str = Field(description="id")


@exclude_graph_model
@entity(description="Relation-classified head", domain=AxisDomain)
class RelationClassifiedHeadEntity(BaseEntity):
    id: str = Field(description="id")
    other: Annotated[AssociationOne[RelationClassifiedOtherEntity], NoInverse()] = Rel(description="a relation")
    pack: Annotated[
        Specialization[RelationClassifiedAlternativeEntity],
        Classifier(field="other", codes=Literal["a"]),
        Inverse(field_name="rec"),
    ] = Rel(description="d")


RelationClassifiedAlternativeEntity.model_rebuild()
RelationClassifiedOtherEntity.model_rebuild()
RelationClassifiedHeadEntity.model_rebuild()


def test_a_classifier_that_is_a_relation_is_refused() -> None:
    assert "is a relation, not a scalar field" in _refuses(
        [RelationClassifiedHeadEntity], "is a relation, not a scalar field"
    )


@exclude_graph_model
@entity(description="Missing-classifier alternative", domain=AxisDomain)
class MissingClassifierAlternativeEntity(BaseEntity):
    id: str = Field(description="id")
    rec: Annotated[
        Generalization[MissingClassifierHeadEntity],
        Classifier("rec", Literal["a"]),
        Inverse(MissingClassifierHeadEntity, "pack"),
    ] = Rel(description="d")


@exclude_graph_model
@entity(description="Missing-classifier head", domain=AxisDomain)
class MissingClassifierHeadEntity(BaseEntity):
    id: str = Field(description="id")
    pack: Annotated[
        Specialization[MissingClassifierAlternativeEntity],
        Classifier(field="nope", codes=Literal["a"]),
        Inverse(field_name="rec"),
    ] = Rel(description="d")


MissingClassifierAlternativeEntity.model_rebuild()
MissingClassifierHeadEntity.model_rebuild()


def test_a_classifier_that_is_not_a_field_is_refused() -> None:
    message = _refuses([MissingClassifierHeadEntity], "is not a field of")
    assert "'nope'" in message


@exclude_graph_model
@entity(description="Self-classified alternative", domain=AxisDomain)
class SelfClassifiedAlternativeEntity(BaseEntity):
    id: str = Field(description="id")
    rec: Annotated[
        Generalization[SelfClassifiedHeadEntity],
        Classifier("rec", Literal["a"]),
        Inverse(SelfClassifiedHeadEntity, "pack"),
    ] = Rel(description="d")


@exclude_graph_model
@entity(description="Self-classified head", domain=AxisDomain)
class SelfClassifiedHeadEntity(BaseEntity):
    id: str = Field(description="id")
    pack: Annotated[
        Specialization[SelfClassifiedAlternativeEntity],
        Classifier(field="pack", codes=Literal["a"]),
        Inverse(field_name="rec"),
    ] = Rel(description="d")


SelfClassifiedAlternativeEntity.model_rebuild()
SelfClassifiedHeadEntity.model_rebuild()


def test_a_classifier_naming_the_axis_itself_is_refused() -> None:
    assert "names the specialization field itself" in _refuses(
        [SelfClassifiedHeadEntity], "names the specialization field itself"
    )


# ─────────────────────────────────────────────────────────────────────────────
# The extension's side of the declaration
# ─────────────────────────────────────────────────────────────────────────────


@exclude_graph_model
@entity(description="Unreachable alternative", domain=AxisDomain)
class UnreachableAlternativeEntity(BaseEntity):
    id: str = Field(description="id")


@exclude_graph_model
@entity(description="Unreachable head", domain=AxisDomain)
class UnreachableHeadEntity(BaseEntity):
    id: str = Field(description="id")
    media: str = Field(description="classifier")
    pack: Annotated[
        Specialization[UnreachableAlternativeEntity],
        Classifier(field="media", codes=Literal["a"]),
        Inverse(field_name="rec"),
    ] = Rel(description="d")


UnreachableAlternativeEntity.model_rebuild()
UnreachableHeadEntity.model_rebuild()


def test_an_alternative_with_no_reverse_field_leaves_the_head_naming_a_code_nobody_owns() -> None:
    """
    The class is in the union, so the head names its code; the class declares nothing, so the
    comparison finds the code orphaned. There is no separate "unreachable" report: this is what
    unreachability looks like from the one place that can see both sides.
    """
    message = _refuses([UnreachableHeadEntity], "no alternative declares them")
    assert "'a'" in message


@exclude_graph_model
@entity(description="Two-way alternative", domain=AxisDomain)
class TwoWayAlternativeEntity(BaseEntity):
    id: str = Field(description="id")
    rec: Annotated[
        Generalization[TwoWayHeadEntity], Classifier("rec", Literal["a"]), Inverse(TwoWayHeadEntity, "pack")
    ] = Rel(description="d")
    rec_again: Annotated[
        Generalization[TwoWayHeadEntity], Classifier("rec_again", Literal["a"]), Inverse(TwoWayHeadEntity, "pack")
    ] = Rel(description="d")


@exclude_graph_model
@entity(description="Two-way head", domain=AxisDomain)
class TwoWayHeadEntity(BaseEntity):
    id: str = Field(description="id")
    media: str = Field(description="classifier")
    pack: Annotated[
        Specialization[TwoWayAlternativeEntity],
        Classifier(field="media", codes=Literal["a"]),
        Inverse(field_name="rec"),
    ] = Rel(description="d")


TwoWayAlternativeEntity.model_rebuild()
TwoWayHeadEntity.model_rebuild()


def test_an_alternative_pointing_back_through_two_fields_is_refused() -> None:
    assert "more than one field" in _refuses([TwoWayHeadEntity], "more than one field")


@exclude_graph_model
@entity(description="Wrongly-paired alternative", domain=AxisDomain)
class WronglyPairedAlternativeEntity(BaseEntity):
    id: str = Field(description="id")
    elsewhere: Annotated[
        Generalization[WronglyPairedHeadEntity],
        Classifier("elsewhere", Literal["a"]),
        Inverse(WronglyPairedHeadEntity, "pack"),
    ] = Rel(description="d")


@exclude_graph_model
@entity(description="Wrongly-paired head", domain=AxisDomain)
class WronglyPairedHeadEntity(BaseEntity):
    id: str = Field(description="id")
    media: str = Field(description="classifier")
    pack: Annotated[
        Specialization[WronglyPairedAlternativeEntity],
        Classifier(field="media", codes=Literal["a"]),
        Inverse(field_name="rec"),
    ] = Rel(description="d")


WronglyPairedAlternativeEntity.model_rebuild()
WronglyPairedHeadEntity.model_rebuild()


def test_an_alternative_paired_through_another_field_name_is_refused() -> None:
    message = _refuses([WronglyPairedHeadEntity], "but the axis names")
    assert "'elsewhere'" in message
    assert "'rec'" in message


# ─────────────────────────────────────────────────────────────────────────────
# A declaration that is right stays right
# ─────────────────────────────────────────────────────────────────────────────


@exclude_graph_model
@entity(description="Good alternative", domain=AxisDomain)
class GoodAlternativeEntity(BaseEntity):
    id: str = Field(description="id")
    rec: Annotated[
        Generalization[GoodHeadEntity], Classifier("rec", Literal["a"]), Inverse(GoodHeadEntity, "pack")
    ] = Rel(description="d")


@exclude_graph_model
@entity(description="Good head", domain=AxisDomain)
class GoodHeadEntity(BaseEntity):
    id: str = Field(description="id")
    media: str = Field(description="classifier")
    pack: Annotated[
        Specialization[GoodAlternativeEntity],
        Classifier(field="media", codes=Literal["a"]),
        Inverse(field_name="rec"),
    ] = Rel(description="d")


GoodAlternativeEntity.model_rebuild()
GoodHeadEntity.model_rebuild()


def test_a_correct_declaration_passes() -> None:
    validate_entity_specializations([GoodHeadEntity])


def test_a_model_without_any_specialization_passes() -> None:
    validate_entity_specializations([])
