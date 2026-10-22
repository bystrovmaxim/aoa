# tests/action_machine/graph/test_entity_specialization_rules_global.py
# ruff: noqa: F821  # the class-name alias is the declaration surface
"""
The rules a specialization must satisfy **across the whole model**: what no single head can decide.

═══════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════

One axis is checked on its own; these are the rules that need the whole walk. A class
claimed by two heads, a class that points at an axis it is not named in, a head that
names itself, two classes that name each other — each is invisible from one head and
plain from the set.

The cases are written in the form the dictionary made current: a head names a closed
dictionary, an alternative names one of its values. The rule that refused two axes on
one classifier field is gone with the field, so it is not among them.

═══════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════

- **SpecializationDeclarationError** — the rule named by each case.

Does not cover what one axis can decide; the axis-rule file beside this one owns that.
"""

from __future__ import annotations

from typing import Annotated

import pytest
from pydantic import Field

from aoa.action_machine.domain import (
    BaseCoreEntity,
    BaseDomain,
    BaseEntity,
    BaseEnumEntity,
    BaseSpecEntity,
    Classifier,
    Generalization,
    Rel,
    Specialization,
)
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


@exclude_graph_model
@entity(description="Kind", domain=GlobalDomain)
class _KindEnumEntity(BaseEnumEntity):
    """The dictionary the cases borrow from."""

    A = _KindEnumEntity(code="a", display_name="A")
    B = _KindEnumEntity(code="b", display_name="B")


# ─────────────────────────────────────────────────────────────────────────────
# A class claimed by two heads
# ─────────────────────────────────────────────────────────────────────────────


@exclude_graph_model
@entity(description="Shared alternative", domain=GlobalDomain)
class SharedAlternativeSpecEntity(BaseSpecEntity):
    """Answers to two heads at once."""

    id: str = Field(description="id")
    first: Annotated[
        Generalization[FirstClaimHeadCoreEntity],
        Classifier(field="first", variant=_KindEnumEntity.A),
    ] = Rel(description="back to the first head")
    second: Annotated[
        Generalization[SecondClaimHeadCoreEntity],
        Classifier(field="second", variant=_KindEnumEntity.B),
    ] = Rel(description="back to the second head")


@exclude_graph_model
@entity(description="First claim", domain=GlobalDomain)
class FirstClaimHeadCoreEntity(BaseCoreEntity):
    """Claims the shared class."""

    id: str = Field(description="id")
    pack: Specialization[SharedAlternativeSpecEntity, _KindEnumEntity] = Rel(description="d")


@exclude_graph_model
@entity(description="Second claim", domain=GlobalDomain)
class SecondClaimHeadCoreEntity(BaseCoreEntity):
    """Claims the same class through its own axis."""

    id: str = Field(description="id")
    pack: Specialization[SharedAlternativeSpecEntity, _KindEnumEntity] = Rel(description="d")


for _cls in (
    SharedAlternativeSpecEntity,
    FirstClaimHeadCoreEntity,
    SecondClaimHeadCoreEntity,
):
    _cls.model_rebuild()


def test_a_class_in_two_unions_is_refused_by_the_claim_not_by_a_symptom() -> None:
    message = _refuses([FirstClaimHeadCoreEntity, SecondClaimHeadCoreEntity], "is an alternative of")
    assert "SharedAlternativeSpecEntity" in message


# ─────────────────────────────────────────────────────────────────────────────
# A class outside the union that points at the axis
# ─────────────────────────────────────────────────────────────────────────────


@exclude_graph_model
@entity(description="Named alternative", domain=GlobalDomain)
class NamedAlternativeSpecEntity(BaseSpecEntity):
    """The class the head actually names."""

    id: str = Field(description="id")
    rec: Annotated[
        Generalization[ClosedHeadCoreEntity],
        Classifier(field="rec", variant=_KindEnumEntity.A),
    ] = Rel(description="back")


@exclude_graph_model
@entity(description="Intruder", domain=GlobalDomain)
class IntruderSpecEntity(BaseSpecEntity):
    """Points at the head without being one of its alternatives."""

    id: str = Field(description="id")
    rec: Generalization[ClosedHeadCoreEntity] = Rel(description="back, but not named")


@exclude_graph_model
@entity(description="Closed head", domain=GlobalDomain)
class ClosedHeadCoreEntity(BaseCoreEntity):
    """Names one alternative, and something else points at it."""

    id: str = Field(description="id")
    pack: Specialization[NamedAlternativeSpecEntity, _KindEnumEntity] = Rel(description="d")


for _cls in (NamedAlternativeSpecEntity, IntruderSpecEntity, ClosedHeadCoreEntity):
    _cls.model_rebuild()


def test_a_class_pointing_at_an_axis_without_being_named_is_refused() -> None:
    message = _refuses(
        [ClosedHeadCoreEntity, IntruderSpecEntity, NamedAlternativeSpecEntity],
        "without being named",
    )
    assert "IntruderSpecEntity" in message


def test_the_named_alternative_itself_is_not_reported_as_an_intruder() -> None:
    message = _refuses(
        [ClosedHeadCoreEntity, IntruderSpecEntity, NamedAlternativeSpecEntity],
        "without being named",
    )
    assert "NamedAlternativeSpecEntity" not in message


# ─────────────────────────────────────────────────────────────────────────────
# Cycles
# ─────────────────────────────────────────────────────────────────────────────


@exclude_graph_model
@entity(description="Self kind", domain=GlobalDomain)
class _SelfKindEnumEntity(BaseEnumEntity):
    """One value, so the cycle rule is what reports the case."""

    A = _SelfKindEnumEntity(code="a", display_name="A")


@exclude_graph_model
@entity(description="Self cycle", domain=GlobalDomain)
class SelfCycleSpecEntity(BaseSpecEntity):
    """Names itself as its own alternative."""

    id: str = Field(description="id")
    rec: Annotated[
        Generalization[SelfCycleSpecEntity],
        Classifier(field="rec", variant=_SelfKindEnumEntity.A),
    ] = Rel(description="back to itself")
    pack: Specialization[SelfCycleSpecEntity, _SelfKindEnumEntity] = Rel(description="names itself")


SelfCycleSpecEntity.model_rebuild()


def test_a_head_naming_itself_is_refused_as_a_cycle() -> None:
    assert "form a cycle" in _refuses([SelfCycleSpecEntity], "form a cycle")


@exclude_graph_model
@entity(description="Cycle A", domain=GlobalDomain)
class CycleASpecEntity(BaseSpecEntity):
    """Names B as its alternative."""

    id: str = Field(description="id")
    rec: Annotated[
        Generalization[CycleBSpecEntity],
        Classifier(field="rec", variant=_KindEnumEntity.A),
    ] = Rel(description="back")


@exclude_graph_model
@entity(description="Cycle B", domain=GlobalDomain)
class CycleBSpecEntity(BaseSpecEntity):
    """Names A as its alternative."""

    id: str = Field(description="id")
    rec: Annotated[
        Generalization[CycleASpecEntity],
        Classifier(field="rec", variant=_KindEnumEntity.B),
    ] = Rel(description="back")
    pack: Specialization[CycleASpecEntity, _KindEnumEntity] = Rel(description="names A")


CycleASpecEntity.model_rebuild()
CycleBSpecEntity.model_rebuild()


def test_a_mutual_cycle_between_two_classes_is_refused_long_before_a_cycle_can_form() -> None:
    """Each names the other, and neither is reachable from its own head's value."""
    assert "no alternative declares them" in _refuses([CycleASpecEntity, CycleBSpecEntity], "no alternative declares them")
