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
    BaseAssocEntity,
    BaseCoreEntity,
    BaseEntity,
    BaseSpecEntity,
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
class StrangerAxisAssocEntity(BaseAssocEntity):
    """Shaped like an entity but never decorated, so the graph would have no node for it."""

    id: str = Field(description="id")


@exclude_graph_model
@entity(description="Stranger head", domain=AxisDomain)
class StrangerHeadCoreEntity(BaseCoreEntity):
    id: str = Field(description="id")
    media: str = Field(description="classifier")
    pack: Annotated[
        Specialization[StrangerAxisAssocEntity], Classifier(field="media", codes=Literal["a"]), Inverse(field_name="rec")
    ] = Rel(description="d")


StrangerHeadCoreEntity.model_rebuild()


def test_an_alternative_that_is_not_a_declared_entity_is_refused() -> None:
    message = _refuses([StrangerHeadCoreEntity], "is not a declared entity")
    assert "StrangerAxisAssocEntity" in message
    assert "@entity" in message, "the message says how to fix it"


# ─────────────────────────────────────────────────────────────────────────────
# The codes, both sides
# ─────────────────────────────────────────────────────────────────────────────


@exclude_graph_model
@entity(description="Silent alternative", domain=AxisDomain)
class SilentAlternativeSpecEntity(BaseSpecEntity):
    id: str = Field(description="id")
    rec: Annotated[Generalization[SilentHeadCoreEntity], Inverse(SilentHeadCoreEntity, "pack")] = Rel(description="no code")


@exclude_graph_model
@entity(description="Silent head", domain=AxisDomain)
class SilentHeadCoreEntity(BaseCoreEntity):
    id: str = Field(description="id")
    media: str = Field(description="classifier")
    pack: Annotated[
        Specialization[SilentAlternativeSpecEntity],
        Classifier(field="media", codes=Literal["a"]),
        Inverse(field_name="rec"),
    ] = Rel(description="d")


SilentAlternativeSpecEntity.model_rebuild()
SilentHeadCoreEntity.model_rebuild()


def test_an_alternative_that_declares_no_code_is_refused() -> None:
    message = _refuses([SilentHeadCoreEntity], "declares no code")
    assert "SilentAlternativeSpecEntity" in message
    assert "rec" in message, "the message names the field that should carry the code"


@exclude_graph_model
@entity(description="Mismatched alternative", domain=AxisDomain)
class MismatchedAlternativeSpecEntity(BaseSpecEntity):
    id: str = Field(description="id")
    rec: Annotated[
        Generalization[MismatchedHeadCoreEntity], Classifier("rec", Literal["other"]), Inverse(MismatchedHeadCoreEntity, "pack")
    ] = Rel(description="d")


@exclude_graph_model
@entity(description="Mismatched head", domain=AxisDomain)
class MismatchedHeadCoreEntity(BaseCoreEntity):
    id: str = Field(description="id")
    media: str = Field(description="classifier")
    pack: Annotated[
        Specialization[MismatchedAlternativeSpecEntity],
        Classifier(field="media", codes=Literal["mine"]),
        Inverse(field_name="rec"),
    ] = Rel(description="d")


MismatchedAlternativeSpecEntity.model_rebuild()
MismatchedHeadCoreEntity.model_rebuild()


def test_a_code_the_head_names_and_no_class_declares_is_refused() -> None:
    message = _refuses([MismatchedHeadCoreEntity], "no alternative declares them")
    assert "mine" in message, "the message names the code that leads nowhere"
    assert "other" not in message, "the error is about the head's side of the comparison"


@exclude_graph_model
@entity(description="Extra alternative", domain=AxisDomain)
class ExtraCodeAlternativeSpecEntity(BaseSpecEntity):
    id: str = Field(description="id")
    rec: Annotated[
        Generalization[ExtraCodeHeadCoreEntity], Classifier("rec", Literal["a"]), Inverse(ExtraCodeHeadCoreEntity, "pack")
    ] = Rel(description="d")


@exclude_graph_model
@entity(description="Extra code head", domain=AxisDomain)
class ExtraCodeHeadCoreEntity(BaseCoreEntity):
    id: str = Field(description="id")
    media: str = Field(description="classifier")
    pack: Annotated[
        Specialization[ExtraCodeAlternativeSpecEntity],
        Classifier(field="media", codes=Literal["a", "b"]),
        Inverse(field_name="rec"),
    ] = Rel(description="d")


ExtraCodeAlternativeSpecEntity.model_rebuild()
ExtraCodeHeadCoreEntity.model_rebuild()


def test_a_code_that_leads_nowhere_is_named_before_the_size_is_compared() -> None:
    """Two codes for one class: the head names a code no alternative answers to, and that is the report."""
    message = _refuses([ExtraCodeHeadCoreEntity], "no alternative declares them")
    assert "'b'" in message


# ─────────────────────────────────────────────────────────────────────────────
# The classifier field
# ─────────────────────────────────────────────────────────────────────────────


@exclude_graph_model
@entity(description="Integer alternative", domain=AxisDomain)
class IntegerAlternativeSpecEntity(BaseSpecEntity):
    id: str = Field(description="id")
    rec: Annotated[
        Generalization[IntegerHeadCoreEntity], Classifier("rec", Literal["a"]), Inverse(IntegerHeadCoreEntity, "pack")
    ] = Rel(description="d")


@exclude_graph_model
@entity(description="Integer head", domain=AxisDomain)
class IntegerHeadCoreEntity(BaseCoreEntity):
    id: str = Field(description="id")
    media: int = Field(description="a numeric classifier cannot hold a word")
    pack: Annotated[
        Specialization[IntegerAlternativeSpecEntity],
        Classifier(field="media", codes=Literal["a"]),
        Inverse(field_name="rec"),
    ] = Rel(description="d")


IntegerAlternativeSpecEntity.model_rebuild()
IntegerHeadCoreEntity.model_rebuild()


def test_a_code_the_classifier_type_cannot_hold_is_refused() -> None:
    message = _refuses([IntegerHeadCoreEntity], "cannot be stored by classifier field")
    assert "'media'" in message
    assert "int" in message, "the message names the type that refused the code"


@exclude_graph_model
@entity(description="Relation-classified alternative", domain=AxisDomain)
class RelationClassifiedAlternativeSpecEntity(BaseSpecEntity):
    id: str = Field(description="id")
    rec: Annotated[
        Generalization[RelationClassifiedHeadAssocEntity],
        Classifier("rec", Literal["a"]),
        Inverse(RelationClassifiedHeadAssocEntity, "pack"),
    ] = Rel(description="d")


@exclude_graph_model
@entity(description="Other side", domain=AxisDomain)
class RelationClassifiedOtherAssocEntity(BaseAssocEntity):
    id: str = Field(description="id")


@exclude_graph_model
@entity(description="Relation-classified head", domain=AxisDomain)
class RelationClassifiedHeadAssocEntity(BaseAssocEntity):
    id: str = Field(description="id")
    other: Annotated[AssociationOne[RelationClassifiedOtherAssocEntity], NoInverse()] = Rel(description="a relation")
    pack: Annotated[
        Specialization[RelationClassifiedAlternativeSpecEntity],
        Classifier(field="other", codes=Literal["a"]),
        Inverse(field_name="rec"),
    ] = Rel(description="d")


RelationClassifiedAlternativeSpecEntity.model_rebuild()
RelationClassifiedOtherAssocEntity.model_rebuild()
RelationClassifiedHeadAssocEntity.model_rebuild()


def test_a_classifier_that_is_a_relation_is_refused() -> None:
    assert "is a relation, not a scalar field" in _refuses(
        [RelationClassifiedHeadAssocEntity], "is a relation, not a scalar field"
    )


@exclude_graph_model
@entity(description="Missing-classifier alternative", domain=AxisDomain)
class MissingClassifierAlternativeSpecEntity(BaseSpecEntity):
    id: str = Field(description="id")
    rec: Annotated[
        Generalization[MissingClassifierHeadAssocEntity],
        Classifier("rec", Literal["a"]),
        Inverse(MissingClassifierHeadAssocEntity, "pack"),
    ] = Rel(description="d")


@exclude_graph_model
@entity(description="Missing-classifier head", domain=AxisDomain)
class MissingClassifierHeadAssocEntity(BaseAssocEntity):
    id: str = Field(description="id")
    pack: Annotated[
        Specialization[MissingClassifierAlternativeSpecEntity],
        Classifier(field="nope", codes=Literal["a"]),
        Inverse(field_name="rec"),
    ] = Rel(description="d")


MissingClassifierAlternativeSpecEntity.model_rebuild()
MissingClassifierHeadAssocEntity.model_rebuild()


def test_a_classifier_that_is_not_a_field_is_refused() -> None:
    message = _refuses([MissingClassifierHeadAssocEntity], "is not a field of")
    assert "'nope'" in message


@exclude_graph_model
@entity(description="Self-classified alternative", domain=AxisDomain)
class SelfClassifiedAlternativeSpecEntity(BaseSpecEntity):
    id: str = Field(description="id")
    rec: Annotated[
        Generalization[SelfClassifiedHeadAssocEntity],
        Classifier("rec", Literal["a"]),
        Inverse(SelfClassifiedHeadAssocEntity, "pack"),
    ] = Rel(description="d")


@exclude_graph_model
@entity(description="Self-classified head", domain=AxisDomain)
class SelfClassifiedHeadAssocEntity(BaseAssocEntity):
    id: str = Field(description="id")
    pack: Annotated[
        Specialization[SelfClassifiedAlternativeSpecEntity],
        Classifier(field="pack", codes=Literal["a"]),
        Inverse(field_name="rec"),
    ] = Rel(description="d")


SelfClassifiedAlternativeSpecEntity.model_rebuild()
SelfClassifiedHeadAssocEntity.model_rebuild()


def test_a_classifier_naming_the_axis_itself_is_refused() -> None:
    assert "names the specialization field itself" in _refuses(
        [SelfClassifiedHeadAssocEntity], "names the specialization field itself"
    )


# ─────────────────────────────────────────────────────────────────────────────
# The extension's side of the declaration
# ─────────────────────────────────────────────────────────────────────────────


@exclude_graph_model
@entity(description="Unreachable alternative", domain=AxisDomain)
class UnreachableAlternativeAssocEntity(BaseAssocEntity):
    id: str = Field(description="id")


@exclude_graph_model
@entity(description="Unreachable head", domain=AxisDomain)
class UnreachableHeadCoreEntity(BaseCoreEntity):
    id: str = Field(description="id")
    media: str = Field(description="classifier")
    pack: Annotated[
        Specialization[UnreachableAlternativeAssocEntity],
        Classifier(field="media", codes=Literal["a"]),
        Inverse(field_name="rec"),
    ] = Rel(description="d")


UnreachableAlternativeAssocEntity.model_rebuild()
UnreachableHeadCoreEntity.model_rebuild()


def test_an_alternative_with_no_reverse_field_leaves_the_head_naming_a_code_nobody_owns() -> None:
    """
    The class is in the union, so the head names its code; the class declares nothing, so the
    comparison finds the code orphaned. There is no separate "unreachable" report: this is what
    unreachability looks like from the one place that can see both sides.
    """
    message = _refuses([UnreachableHeadCoreEntity], "no alternative declares them")
    assert "'a'" in message


@exclude_graph_model
@entity(description="Two-way alternative", domain=AxisDomain)
class TwoWayAlternativeSpecEntity(BaseSpecEntity):
    id: str = Field(description="id")
    rec: Annotated[
        Generalization[TwoWayHeadCoreEntity], Classifier("rec", Literal["a"]), Inverse(TwoWayHeadCoreEntity, "pack")
    ] = Rel(description="d")
    rec_again: Annotated[
        Generalization[TwoWayHeadCoreEntity], Classifier("rec_again", Literal["a"]), Inverse(TwoWayHeadCoreEntity, "pack")
    ] = Rel(description="d")


@exclude_graph_model
@entity(description="Two-way head", domain=AxisDomain)
class TwoWayHeadCoreEntity(BaseCoreEntity):
    id: str = Field(description="id")
    media: str = Field(description="classifier")
    pack: Annotated[
        Specialization[TwoWayAlternativeSpecEntity],
        Classifier(field="media", codes=Literal["a"]),
        Inverse(field_name="rec"),
    ] = Rel(description="d")


TwoWayAlternativeSpecEntity.model_rebuild()
TwoWayHeadCoreEntity.model_rebuild()


def test_an_alternative_pointing_back_through_two_fields_is_refused() -> None:
    assert "more than one field" in _refuses([TwoWayHeadCoreEntity], "more than one field")


@exclude_graph_model
@entity(description="Wrongly-paired alternative", domain=AxisDomain)
class WronglyPairedAlternativeSpecEntity(BaseSpecEntity):
    id: str = Field(description="id")
    elsewhere: Annotated[
        Generalization[WronglyPairedHeadCoreEntity],
        Classifier("elsewhere", Literal["a"]),
        Inverse(WronglyPairedHeadCoreEntity, "pack"),
    ] = Rel(description="d")


@exclude_graph_model
@entity(description="Wrongly-paired head", domain=AxisDomain)
class WronglyPairedHeadCoreEntity(BaseCoreEntity):
    id: str = Field(description="id")
    media: str = Field(description="classifier")
    pack: Annotated[
        Specialization[WronglyPairedAlternativeSpecEntity],
        Classifier(field="media", codes=Literal["a"]),
        Inverse(field_name="rec"),
    ] = Rel(description="d")


WronglyPairedAlternativeSpecEntity.model_rebuild()
WronglyPairedHeadCoreEntity.model_rebuild()


def test_an_alternative_paired_through_another_field_name_is_refused() -> None:
    message = _refuses([WronglyPairedHeadCoreEntity], "but the axis names")
    assert "'elsewhere'" in message
    assert "'rec'" in message


# ─────────────────────────────────────────────────────────────────────────────
# A declaration that is right stays right
# ─────────────────────────────────────────────────────────────────────────────


@exclude_graph_model
@entity(description="Good alternative", domain=AxisDomain)
class GoodAlternativeSpecEntity(BaseSpecEntity):
    id: str = Field(description="id")
    rec: Annotated[
        Generalization[GoodHeadCoreEntity], Classifier("rec", Literal["a"]), Inverse(GoodHeadCoreEntity, "pack")
    ] = Rel(description="d")


@exclude_graph_model
@entity(description="Good head", domain=AxisDomain)
class GoodHeadCoreEntity(BaseCoreEntity):
    id: str = Field(description="id")
    media: str = Field(description="classifier")
    pack: Annotated[
        Specialization[GoodAlternativeSpecEntity],
        Classifier(field="media", codes=Literal["a"]),
        Inverse(field_name="rec"),
    ] = Rel(description="d")


GoodAlternativeSpecEntity.model_rebuild()
GoodHeadCoreEntity.model_rebuild()


def test_a_correct_declaration_passes() -> None:
    validate_entity_specializations([GoodHeadCoreEntity])


def test_a_model_without_any_specialization_passes() -> None:
    validate_entity_specializations([])
