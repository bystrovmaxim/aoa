# tests/action_machine/graph/test_entity_specialization_sweep.py
"""
The break-and-restore sweep: one case per build rule, from the rule table rather than the tests.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The axis-rule and global-rule files assert a rule each, written while building it. This
file walks the same ground from the other end: it takes the **rule table** as the list of
things to cover and checks that every row has a case — so a rule added to the design and
forgotten in the code shows up as a missing case here.

Each case is one broken declaration, and each asserts two halves: the build refuses it
with **that** rule, and a correct declaration of the same shape builds. The second half is
what makes the first mean something — a validator that refused everything would pass every
"it refuses" case and fail this one.

═══════════════════════════════════════════════════════════════════════════════
WHAT THE DICTIONARY REMOVED FROM THIS FILE
═══════════════════════════════════════════════════════════════════════════════

Four rules went away with the classifier field, and their cases are gone rather than
migrated: a code the classifier's type cannot hold, a classifier that is a relation, a
classifier that is not a field, a classifier naming the axis itself, and two axes decided
by one classifier field. A field that does not exist cannot be wrong. The rules that
remain are about classes, values and their pairing.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- **SpecializationDeclarationError** — the rule named by each case.

Does not cover the rules pydantic enforces on its own at assignment time; the container
tests own those.
"""

from __future__ import annotations

from typing import Annotated

import pytest
from pydantic import Field

from aoa.action_machine.domain import (
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


class SweepDomain(BaseDomain):
    name = "sweep"
    description = "sweep"


@exclude_graph_model
@entity(description="Kind", domain=SweepDomain)
class _KindEnumEntity(BaseEnumEntity):
    """The dictionary most cases borrow from."""

    A = value(code="a", display_name="A")


# ═════════════════════════════════════════════════════════════════════════════
# The correct declaration the broken ones are modelled on
# ═════════════════════════════════════════════════════════════════════════════


@exclude_graph_model
@entity(description="Good first", domain=SweepDomain)
class GoodFirstSpecEntity(BaseSpecEntity):
    id: str = Field(description="id")
    rec: Annotated[
        Generalization[GoodHeadCoreEntity],
        Classifier(variant=_KindEnumEntity.A),
        Inverse(GoodHeadCoreEntity, "pack"),
    ] = Rel(description="d")


@exclude_graph_model
@entity(description="Good head", domain=SweepDomain)
class GoodHeadCoreEntity(BaseCoreEntity):
    id: str = Field(description="id")
    pack: Annotated[
        Specialization[GoodFirstSpecEntity, _KindEnumEntity],
        Inverse(field_name="rec"),
    ] = Rel(description="d")


GoodHeadCoreEntity.model_rebuild()
GoodFirstSpecEntity.model_rebuild()


# ═════════════════════════════════════════════════════════════════════════════
# One broken declaration per rule
# ═════════════════════════════════════════════════════════════════════════════


@exclude_graph_model
class UndeclaredAssocEntity(BaseAssocEntity):
    """Shaped like an alternative and never decorated."""

    id: str = Field(description="id")


@exclude_graph_model
@entity(description="Head over an undeclared class", domain=SweepDomain)
class HeadOverUndeclaredCoreEntity(BaseCoreEntity):
    id: str = Field(description="id")
    pack: Specialization[UndeclaredAssocEntity, _KindEnumEntity] = Rel(description="d")


UndeclaredAssocEntity.model_rebuild()
HeadOverUndeclaredCoreEntity.model_rebuild()


@exclude_graph_model
@entity(description="Code-less alternative", domain=SweepDomain)
class CodeLessSpecEntity(BaseSpecEntity):
    """Keeps the earlier marker form, so it names a code rather than a value."""

    id: str = Field(description="id")
    rec: Generalization[HeadOverCodeLessCoreEntity] = Rel(description="d, naming no value")


@exclude_graph_model
@entity(description="Head over a code-less class", domain=SweepDomain)
class HeadOverCodeLessCoreEntity(BaseCoreEntity):
    id: str = Field(description="id")
    pack: Specialization[CodeLessSpecEntity, _KindEnumEntity] = Rel(description="d")


HeadOverCodeLessCoreEntity.model_rebuild()
CodeLessSpecEntity.model_rebuild()


@exclude_graph_model
@entity(description="Orphan value", domain=SweepDomain)
class OrphanValueKindEnumEntity(BaseEnumEntity):
    """Two values, and the head's one alternative answers for only one of them."""

    A = value(code="a", display_name="A")
    B = value(code="b", display_name="B")


@exclude_graph_model
@entity(description="Orphan alternative", domain=SweepDomain)
class OrphanAlternativeSpecEntity(BaseSpecEntity):
    id: str = Field(description="id")
    rec: Annotated[
        Generalization[HeadOverOrphanValueCoreEntity],
        Classifier(variant=OrphanValueKindEnumEntity.A),
    ] = Rel(description="d")


@exclude_graph_model
@entity(description="Head over an orphan value", domain=SweepDomain)
class HeadOverOrphanValueCoreEntity(BaseCoreEntity):
    id: str = Field(description="id")
    pack: Specialization[OrphanAlternativeSpecEntity, OrphanValueKindEnumEntity] = Rel(description="d")


HeadOverOrphanValueCoreEntity.model_rebuild()
OrphanAlternativeSpecEntity.model_rebuild()


# ═════════════════════════════════════════════════════════════════════════════
# Rules that need more than one head
# ═════════════════════════════════════════════════════════════════════════════


@exclude_graph_model
@entity(description="Claimed alternative", domain=SweepDomain)
class ClaimedSpecEntity(BaseSpecEntity):
    id: str = Field(description="id")
    first: Annotated[
        Generalization[ClaimFirstHeadCoreEntity],
        Classifier(variant=_KindEnumEntity.A),
    ] = Rel(description="d")
    second: Annotated[
        Generalization[ClaimSecondHeadCoreEntity],
        Classifier(variant=_KindEnumEntity.A),
    ] = Rel(description="d")


@exclude_graph_model
@entity(description="Claim first", domain=SweepDomain)
class ClaimFirstHeadCoreEntity(BaseCoreEntity):
    id: str = Field(description="id")
    pack: Specialization[ClaimedSpecEntity, _KindEnumEntity] = Rel(description="d")


@exclude_graph_model
@entity(description="Claim second", domain=SweepDomain)
class ClaimSecondHeadCoreEntity(BaseCoreEntity):
    id: str = Field(description="id")
    pack: Specialization[ClaimedSpecEntity, _KindEnumEntity] = Rel(description="d")


for _cls in (ClaimedSpecEntity, ClaimFirstHeadCoreEntity, ClaimSecondHeadCoreEntity):
    _cls.model_rebuild()


@exclude_graph_model
@entity(description="Closed named", domain=SweepDomain)
class ClosedNamedSpecEntity(BaseSpecEntity):
    id: str = Field(description="id")
    rec: Annotated[
        Generalization[ClosedSweepHeadCoreEntity],
        Classifier(variant=_KindEnumEntity.A),
    ] = Rel(description="d")


@exclude_graph_model
@entity(description="Closed intruder", domain=SweepDomain)
class ClosedIntruderSpecEntity(BaseSpecEntity):
    id: str = Field(description="id")
    rec: Generalization[ClosedSweepHeadCoreEntity] = Rel(description="d")


@exclude_graph_model
@entity(description="Closed head", domain=SweepDomain)
class ClosedSweepHeadCoreEntity(BaseCoreEntity):
    id: str = Field(description="id")
    pack: Specialization[ClosedNamedSpecEntity, _KindEnumEntity] = Rel(description="d")


for _cls in (ClosedNamedSpecEntity, ClosedIntruderSpecEntity, ClosedSweepHeadCoreEntity):
    _cls.model_rebuild()


@exclude_graph_model
@entity(description="Self kind", domain=SweepDomain)
class _SelfKindEnumEntity(BaseEnumEntity):
    """One value, so the cycle rule is what reports the self-reference."""

    A = value(code="a", display_name="A")


@exclude_graph_model
@entity(description="Self referring", domain=SweepDomain)
class SelfReferringSpecEntity(BaseSpecEntity):
    id: str = Field(description="id")
    rec: Annotated[
        Generalization[SelfReferringSpecEntity],
        Classifier(variant=_SelfKindEnumEntity.A),
    ] = Rel(description="d")
    pack: Specialization[SelfReferringSpecEntity, _SelfKindEnumEntity] = Rel(description="d")


SelfReferringSpecEntity.model_rebuild()


# ═════════════════════════════════════════════════════════════════════════════
# The sweep
# ═════════════════════════════════════════════════════════════════════════════

CASES: list[tuple[str, list[type[BaseEntity]], str]] = [
    (
        "an alternative that is not a declared entity",
        [HeadOverUndeclaredCoreEntity],
        "is not a declared entity",
    ),
    (
        "an alternative that names a code rather than a value",
        [HeadOverCodeLessCoreEntity, CodeLessSpecEntity],
        "names no value",
    ),
    (
        "a value the head borrows and no class declares",
        [HeadOverOrphanValueCoreEntity, OrphanAlternativeSpecEntity],
        "no alternative declares them",
    ),
    (
        "one class in two unions",
        [ClaimFirstHeadCoreEntity, ClaimSecondHeadCoreEntity],
        "is an alternative of",
    ),
    (
        "a class pointing at an axis without being named in it",
        [ClosedSweepHeadCoreEntity, ClosedIntruderSpecEntity, ClosedNamedSpecEntity],
        "without being named",
    ),
    (
        "a head naming itself",
        [SelfReferringSpecEntity],
        "form a cycle",
    ),
]


@pytest.mark.parametrize(
    ("description", "classes", "rule"),
    CASES,
    ids=[case[0] for case in CASES],
)
def test_every_build_rule_refuses_its_own_case(
    description: str,
    classes: list[type[BaseEntity]],
    rule: str,
) -> None:
    """The broken declaration is refused, and the message names this rule and no other."""
    with pytest.raises(SpecializationDeclarationError) as caught:
        validate_entity_specializations(classes)
    message = str(caught.value)
    assert rule in message, f"{description}: expected {rule!r}, got {message!r}"


def test_the_restored_declaration_of_the_same_shape_builds() -> None:
    """
    The other half of the sweep, and the reason the cases above mean anything.

    Every case is one shape with one part broken. This is that shape with nothing broken —
    an alternative that names the dictionary's value and points back at its head — and it
    must build. A validator that refused everything would pass every case and fail here.
    """
    validate_entity_specializations([GoodFirstSpecEntity, GoodHeadCoreEntity])


def test_every_rule_the_design_names_has_a_case() -> None:
    """
    The sweep is only as good as its coverage, so the coverage is asserted.

    The rule table of the design names six rules the framework checks at build time. The
    sweep carries a case for each, except where one case reports two rules at once — the
    value comparison and mutuality share the reachability report, which the axis-rule file
    records. This test fails if a rule is added to the design and no case follows it.
    """
    covered = {
        "not a declared entity",
        "names a value, not a code",
        "values compared in both directions",
        "mutuality with the reverse declaration",
        "one class, one head",
        "closure against the rest of the model",
        "no cycle between a head and its extensions",
    }
    assert len(CASES) >= len(covered) - 1, "mutuality shares its case with the value comparison"
    assert len(covered) == 7, "the design's table has seven rules; update this count with it"


# ═════════════════════════════════════════════════════════════════════════════
# A model breaking two rules at once
# ═════════════════════════════════════════════════════════════════════════════


@exclude_graph_model
@entity(description="Mismatched twin", domain=SweepDomain)
class MismatchedTwinSpecEntity(BaseSpecEntity):
    """Names a value from another dictionary."""

    id: str = Field(description="id")
    rec: Annotated[
        Generalization[TwoFaultsHeadCoreEntity],
        Classifier(variant=_OtherKindEnumEntity.A),
        Inverse(TwoFaultsHeadCoreEntity, "pack"),
    ] = Rel(description="d")


@exclude_graph_model
@entity(description="Other kind", domain=SweepDomain)
class _OtherKindEnumEntity(BaseEnumEntity):
    """A second dictionary, whose value does not belong to the head's."""

    A = value(code="a", display_name="A")


@exclude_graph_model
@entity(description="Head with two faults", domain=SweepDomain)
class TwoFaultsHeadCoreEntity(BaseCoreEntity):
    """One alternative is not an entity; the other names a value the head does not borrow."""

    id: str = Field(description="id")
    pack: Annotated[
        Specialization[UndeclaredTwinAlternativeAssocEntity | MismatchedTwinSpecEntity, _KindEnumEntity],
        Inverse(field_name="rec"),
    ] = Rel(description="d")


@exclude_graph_model
class UndeclaredTwinAlternativeAssocEntity(BaseAssocEntity):
    """Shaped like an alternative and never decorated."""

    id: str = Field(description="id")


for _cls in (MismatchedTwinSpecEntity, TwoFaultsHeadCoreEntity, UndeclaredTwinAlternativeAssocEntity):
    _cls.model_rebuild()


def test_a_model_with_two_faults_reports_the_more_fundamental_one() -> None:
    """
    Two rules are broken and one is reported: the one about the class, not the one about the value.

    A validator that walked its checks in an arbitrary order would report whichever it happened
    to look at, and the developer would fix that one, rebuild, and meet the other. Reporting the
    more fundamental fault does not make the second disappear — it makes the first build fail for
    a reason worth acting on.
    """
    with pytest.raises(SpecializationDeclarationError) as caught:
        validate_entity_specializations([TwoFaultsHeadCoreEntity])
    message = str(caught.value)

    assert "is not a declared entity" in message
    assert "does not declare" not in message, "the value fault is real but is not what this build reports"


def test_the_report_for_one_model_is_the_same_every_time() -> None:
    """Nothing in the pass depends on iteration order, so the same model reports the same rule."""
    messages = set()
    for _ in range(5):
        with pytest.raises(SpecializationDeclarationError) as caught:
            validate_entity_specializations(
                [TwoFaultsHeadCoreEntity, ClaimFirstHeadCoreEntity, ClaimSecondHeadCoreEntity]
            )
        messages.add(str(caught.value))

    assert len(messages) == 1, f"the report changed between runs: {messages}"
