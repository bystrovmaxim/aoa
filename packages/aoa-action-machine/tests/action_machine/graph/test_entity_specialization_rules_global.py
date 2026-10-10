# tests/action_machine/graph/test_entity_specialization_rules_global.py
"""
The rules a specialization must satisfy **across the whole model**: what no single head can decide.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Some defects are invisible from one head. A class claimed by two heads looks fine from
each of them; two axes sharing a classifier look fine until both are known; a class
pointing at a field it is not named in looks fine until the union is compared with the
model. These tests build one such model each and assert the build refuses it with the
named rule.

═══════════════════════════════════════════════════════════════════════════════
PRECEDENCE, WHICH IS PART OF THE CONTRACT
═══════════════════════════════════════════════════════════════════════════════

A global rule is reported **before** the per-axis rules of the same model, and that is
deliberate: when a class is claimed by two heads, the per-axis rules see the second head
as an alternative that forgot to point back. That is true and it is not the reason, so
the tests here assert the cause and not the symptom.

═══════════════════════════════════════════════════════════════════════════════
A CYCLE THAT CANNOT BE WRITTEN
═══════════════════════════════════════════════════════════════════════════════

A cycle between two distinct classes cannot reach the cycle rule, and this file records
why rather than pretending otherwise: for A to name B and B to name A, each class would
have to be an alternative of the other's union, which the one-head-per-class rule refuses
first. What the cycle rule does catch is **self-reference** — a head naming itself as its
own alternative — and that is the case the test below builds.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- **SpecializationDeclarationError** — the rule named in each test.

Does not cover what one axis can decide; the axis-rule file beside this one owns that.
"""

from __future__ import annotations

from typing import Annotated, Literal

import pytest
from pydantic import Field

from aoa.action_machine.domain import (
    BaseEntity,
    Classifier,
    Generalization,
    Inverse,
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


class GlobalDomain(BaseDomain):
    name = "global"
    description = "global"


def _refuses(classes: list[type[BaseEntity]], rule: str) -> str:
    """Assert the build refuses ``classes`` with ``rule`` and return the message."""
    with pytest.raises(SpecializationDeclarationError) as caught:
        validate_entity_specializations(classes)
    message = str(caught.value)
    assert rule in message, message
    return message


# ─────────────────────────────────────────────────────────────────────────────
# A class claimed by two heads
# ─────────────────────────────────────────────────────────────────────────────


@exclude_graph_model
@entity(description="Shared class", domain=GlobalDomain)
class SharedClassEntity(BaseEntity):
    """Points back at one head; the other head names it too, which is the defect."""

    id: str = Field(description="id")
    rec: Annotated[
        Generalization[FirstClaimHeadEntity], Classifier("rec", Literal["a"]), Inverse(FirstClaimHeadEntity, "pack")
    ] = Rel(description="d")


@exclude_graph_model
@entity(description="First claim head", domain=GlobalDomain)
class FirstClaimHeadEntity(BaseEntity):
    id: str = Field(description="id")
    media: str = Field(description="classifier")
    pack: Annotated[
        Specialization[SharedClassEntity],
        Classifier(field="media", codes=Literal["a"]),
        Inverse(field_name="rec"),
    ] = Rel(description="d")


@exclude_graph_model
@entity(description="Second claim head", domain=GlobalDomain)
class SecondClaimHeadEntity(BaseEntity):
    id: str = Field(description="id")
    media: str = Field(description="classifier")
    pack: Annotated[
        Specialization[SharedClassEntity],
        Classifier(field="media", codes=Literal["a"]),
        Inverse(field_name="rec"),
    ] = Rel(description="d")


SharedClassEntity.model_rebuild()
FirstClaimHeadEntity.model_rebuild()
SecondClaimHeadEntity.model_rebuild()


def test_a_class_in_two_unions_is_refused_by_the_claim_not_by_a_symptom() -> None:
    message = _refuses([FirstClaimHeadEntity, SecondClaimHeadEntity], "is an alternative of")
    assert "SharedClassEntity" in message
    assert "FirstClaimHeadEntity" in message, "the message names the head that claimed it first"
    assert "SecondClaimHeadEntity" in message


# ─────────────────────────────────────────────────────────────────────────────
# Two axes decided by one field
# ─────────────────────────────────────────────────────────────────────────────


@exclude_graph_model
@entity(description="First alternative", domain=GlobalDomain)
class FirstSharedClassifierAlternativeEntity(BaseEntity):
    id: str = Field(description="id")
    rec: Annotated[
        Generalization[SharedClassifierHeadEntity],
        Classifier("rec", Literal["a"]),
        Inverse(SharedClassifierHeadEntity, "pack"),
    ] = Rel(description="d")


@exclude_graph_model
@entity(description="Second alternative", domain=GlobalDomain)
class SecondSharedClassifierAlternativeEntity(BaseEntity):
    id: str = Field(description="id")
    rec: Annotated[
        Generalization[SharedClassifierHeadEntity],
        Classifier("rec", Literal["b"]),
        Inverse(SharedClassifierHeadEntity, "other_pack"),
    ] = Rel(description="d")


@exclude_graph_model
@entity(description="Shared classifier head", domain=GlobalDomain)
class SharedClassifierHeadEntity(BaseEntity):
    id: str = Field(description="id")
    media: str = Field(description="one classifier cannot decide two axes")
    pack: Annotated[
        Specialization[FirstSharedClassifierAlternativeEntity],
        Classifier(field="media", codes=Literal["a"]),
        Inverse(field_name="rec"),
    ] = Rel(description="d")
    other_pack: Annotated[
        Specialization[SecondSharedClassifierAlternativeEntity],
        Classifier(field="media", codes=Literal["b"]),
        Inverse(field_name="rec"),
    ] = Rel(description="d")


FirstSharedClassifierAlternativeEntity.model_rebuild()
SecondSharedClassifierAlternativeEntity.model_rebuild()
SharedClassifierHeadEntity.model_rebuild()


def test_two_axes_on_one_classifier_field_are_refused() -> None:
    message = _refuses([SharedClassifierHeadEntity], "already decides")
    assert "'media'" in message
    assert "pack" in message, "the message names the axis that already owns the field"


# ─────────────────────────────────────────────────────────────────────────────
# Closure: a class pointing at a field it is not named in
# ─────────────────────────────────────────────────────────────────────────────


@exclude_graph_model
@entity(description="Named alternative", domain=GlobalDomain)
class NamedAlternativeEntity(BaseEntity):
    id: str = Field(description="id")
    rec: Annotated[
        Generalization[ClosedHeadEntity], Classifier("rec", Literal["a"]), Inverse(ClosedHeadEntity, "pack")
    ] = Rel(description="d")


@exclude_graph_model
@entity(description="Intruder", domain=GlobalDomain)
class IntruderEntity(BaseEntity):
    """Points at the head's field without being named in the union."""

    id: str = Field(description="id")
    rec: Annotated[Generalization[ClosedHeadEntity], Classifier("rec", Literal["b"])] = Rel(description="d")


@exclude_graph_model
@entity(description="Closed head", domain=GlobalDomain)
class ClosedHeadEntity(BaseEntity):
    id: str = Field(description="id")
    media: str = Field(description="classifier")
    pack: Annotated[
        Specialization[NamedAlternativeEntity],
        Classifier(field="media", codes=Literal["a"]),
        Inverse(field_name="rec"),
    ] = Rel(description="d")


NamedAlternativeEntity.model_rebuild()
IntruderEntity.model_rebuild()
ClosedHeadEntity.model_rebuild()


def test_a_class_pointing_at_an_axis_without_being_named_is_refused() -> None:
    """
    The intruder is passed in explicitly, and here is why that is the honest form of the test.

    Both classes are fixtures marked ``@exclude_graph_model``, so a build does not judge them
    at all. Judging them is exactly what this test asks for — so it hands over the head **and**
    the class that points at it, and the rule that compares the union against the model reports
    the one that is not named. A test that passed only the head would be asking whether an
    excluded class is judged, and the answer to that is no by design.
    """
    message = _refuses([ClosedHeadEntity, IntruderEntity, NamedAlternativeEntity], "without being named")
    assert "IntruderEntity" in message
    assert "pack" in message
    assert "add it to the alternatives" in message, "the message says what to do"


def test_the_named_alternative_itself_is_not_reported_as_an_intruder() -> None:
    """The message names the intruder only; the class that belongs is silent."""
    message = _refuses([ClosedHeadEntity, IntruderEntity, NamedAlternativeEntity], "without being named")
    assert "NamedAlternativeEntity" not in message


# ─────────────────────────────────────────────────────────────────────────────
# A head naming itself
# ─────────────────────────────────────────────────────────────────────────────


@exclude_graph_model
@entity(description="Self cycle", domain=GlobalDomain)
class SelfCycleEntity(BaseEntity):
    """A head that names itself as its own alternative."""

    id: str = Field(description="id")
    media: str = Field(description="classifier")
    back: Annotated[
        Generalization[SelfCycleEntity], Classifier("back", Literal["a"]), Inverse(SelfCycleEntity, "loop")
    ] = Rel(description="d")
    loop: Annotated[
        Specialization[SelfCycleEntity],
        Classifier(field="media", codes=Literal["a"]),
        Inverse(field_name="back"),
    ] = Rel(description="d")


SelfCycleEntity.model_rebuild()


def test_a_head_naming_itself_is_refused_as_a_cycle() -> None:
    message = _refuses([SelfCycleEntity], "form a cycle")
    assert "SelfCycleEntity -> SelfCycleEntity" in message, "the message draws the cycle"


@exclude_graph_model
@entity(description="Cycle A", domain=GlobalDomain)
class CycleAEntity(BaseEntity):
    """Half of a mutual cycle, with the reverse field the other half would need."""

    id: str = Field(description="id")
    media: str = Field(description="classifier")
    other: Annotated[
        Specialization[CycleBEntity], Classifier(field="media", codes=Literal["b"]), Inverse(field_name="back")
    ] = Rel(description="d")
    back: Annotated[
        Generalization[CycleBEntity], Classifier("back", Literal["b"]), Inverse(CycleBEntity, "other")
    ] = Rel(description="d")


@exclude_graph_model
@entity(description="Cycle B", domain=GlobalDomain)
class CycleBEntity(BaseEntity):
    """The other half: naming A back makes both classes alternatives of each other."""

    id: str = Field(description="id")
    media: str = Field(description="classifier")
    other: Annotated[
        Specialization[CycleAEntity], Classifier(field="media", codes=Literal["a"]), Inverse(field_name="back")
    ] = Rel(description="d")
    back: Annotated[
        Generalization[CycleAEntity], Classifier("back", Literal["a"]), Inverse(CycleAEntity, "other")
    ] = Rel(description="d")


CycleAEntity.model_rebuild()
CycleBEntity.model_rebuild()


def test_a_mutual_cycle_between_two_classes_is_refused_long_before_a_cycle_can_form() -> None:
    """
    The pair is refused, and not by the cycle rule — by the code comparison, three guards early.

    Measured, because it decides what this rule is for: A names B, B names A, and each declares
    a code for the other. The parser reads a class's code from the field that points **at its own
    head**, and neither of these fields does, so neither code is found. The two-sided comparison
    reports the orphaned codes before any rule about pairs is reached. Mutual reference is
    therefore refused by the first guard that can see it, not by the last, and the cycle rule's
    reachable case is self-reference — the test above.

    This test pins the refusal and names the guard. It deliberately does **not** pin which of the
    three could speak first, because two of them never get the chance.
    """
    message = _refuses([CycleAEntity, CycleBEntity], "no alternative declares them")
    assert "CycleAEntity" in message
