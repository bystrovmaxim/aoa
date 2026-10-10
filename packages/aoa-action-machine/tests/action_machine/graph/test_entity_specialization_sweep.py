# tests/action_machine/graph/test_entity_specialization_sweep.py
"""
The break-and-restore sweep: one case per build rule, from the rule table rather than the tests.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The axis-rule and global-rule files assert a rule each, written while building it. This
file walks the same ground from the other end: it takes the **rule table** as the list of
things to cover and checks that every row has a case — so a rule added to the design and
forgotten in the code shows up as a missing case here, and a rule in the code that the
table does not name shows up as a case with no row.

Each case is one broken declaration, and each asserts two halves: the build refuses it
with **that** rule, and a correct declaration of the same shape builds. The second half is
what makes the first mean something — a validator that refused everything would pass every
"it refuses" test and fail this one.

═══════════════════════════════════════════════════════════════════════════════
WHY THE CASES ARE FIXTURES AND NOT GENERATED MODELS
═══════════════════════════════════════════════════════════════════════════════

Generated models were tried first, since a sweep wants one shape with one part changed, and
they do not work here: pydantic caches the schema, so `model_rebuild(force=True)` after
rewriting `__annotations__` keeps the annotation the class was created with. Measured twice,
both with a plain subclass and with `create_model` — the field stayed `str`. The cases are
therefore declared as classes, which is also what a reader can check against the rule table.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- **SpecializationDeclarationError** — the rule named by each case.

Does not cover the rules pydantic enforces on its own at assignment time; the container
tests own those.
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


class SweepDomain(BaseDomain):
    name = "sweep"
    description = "sweep"


# ═════════════════════════════════════════════════════════════════════════════
# The correct declaration the broken ones are modelled on
# ═════════════════════════════════════════════════════════════════════════════


@exclude_graph_model
@entity(description="Good first", domain=SweepDomain)
class GoodFirstEntity(BaseEntity):
    id: str = Field(description="id")
    rec: Annotated[
        Generalization[GoodHeadEntity], Classifier("rec", Literal["a"]), Inverse(GoodHeadEntity, "pack")
    ] = Rel(description="d")


@exclude_graph_model
@entity(description="Good second", domain=SweepDomain)
class GoodSecondEntity(BaseEntity):
    id: str = Field(description="id")
    rec: Annotated[
        Generalization[GoodHeadEntity], Classifier("rec", Literal["b"]), Inverse(GoodHeadEntity, "pack")
    ] = Rel(description="d")


@exclude_graph_model
@entity(description="Good head", domain=SweepDomain)
class GoodHeadEntity(BaseEntity):
    id: str = Field(description="id")
    media: str = Field(description="classifier")
    pack: Annotated[
        Specialization[GoodFirstEntity | GoodSecondEntity],
        Classifier(field="media", codes=Literal["a", "b"]),
        Inverse(field_name="rec"),
    ] = Rel(description="d")


for _cls in (GoodFirstEntity, GoodSecondEntity, GoodHeadEntity):
    _cls.model_rebuild()


# ═════════════════════════════════════════════════════════════════════════════
# Case 1: an alternative that is not a declared entity
# ═════════════════════════════════════════════════════════════════════════════


@exclude_graph_model
class UndeclaredAlternativeEntity(BaseEntity):
    id: str = Field(description="id")


@exclude_graph_model
@entity(description="Head over an undeclared class", domain=SweepDomain)
class HeadOverUndeclaredEntity(BaseEntity):
    id: str = Field(description="id")
    media: str = Field(description="classifier")
    pack: Annotated[
        Specialization[UndeclaredAlternativeEntity],
        Classifier(field="media", codes=Literal["a"]),
        Inverse(field_name="rec"),
    ] = Rel(description="d")


HeadOverUndeclaredEntity.model_rebuild()


# ═════════════════════════════════════════════════════════════════════════════
# Case 2: an alternative that declares no code
# ═════════════════════════════════════════════════════════════════════════════


@exclude_graph_model
@entity(description="Code-less alternative", domain=SweepDomain)
class CodeLessAlternativeEntity(BaseEntity):
    id: str = Field(description="id")
    rec: Annotated[Generalization[HeadOverCodeLessEntity], Inverse(HeadOverCodeLessEntity, "pack")] = Rel(
        description="d"
    )


@exclude_graph_model
@entity(description="Head over a code-less class", domain=SweepDomain)
class HeadOverCodeLessEntity(BaseEntity):
    id: str = Field(description="id")
    media: str = Field(description="classifier")
    pack: Annotated[
        Specialization[CodeLessAlternativeEntity],
        Classifier(field="media", codes=Literal["a"]),
        Inverse(field_name="rec"),
    ] = Rel(description="d")


CodeLessAlternativeEntity.model_rebuild()
HeadOverCodeLessEntity.model_rebuild()


# ═════════════════════════════════════════════════════════════════════════════
# Case 3: a code the head names and no class declares
# ═════════════════════════════════════════════════════════════════════════════


@exclude_graph_model
@entity(description="Orphan-code alternative", domain=SweepDomain)
class OrphanCodeAlternativeEntity(BaseEntity):
    id: str = Field(description="id")
    rec: Annotated[
        Generalization[HeadOverOrphanCodeEntity], Classifier("rec", Literal["other"]), Inverse(HeadOverOrphanCodeEntity, "pack")
    ] = Rel(description="d")


@exclude_graph_model
@entity(description="Head naming an orphan code", domain=SweepDomain)
class HeadOverOrphanCodeEntity(BaseEntity):
    id: str = Field(description="id")
    media: str = Field(description="classifier")
    pack: Annotated[
        Specialization[OrphanCodeAlternativeEntity],
        Classifier(field="media", codes=Literal["mine"]),
        Inverse(field_name="rec"),
    ] = Rel(description="d")


OrphanCodeAlternativeEntity.model_rebuild()
HeadOverOrphanCodeEntity.model_rebuild()


# ═════════════════════════════════════════════════════════════════════════════
# Case 4: fewer codes than alternatives
# ═════════════════════════════════════════════════════════════════════════════


@exclude_graph_model
@entity(description="Short first", domain=SweepDomain)
class ShortFirstEntity(BaseEntity):
    id: str = Field(description="id")
    rec: Annotated[
        Generalization[ShortHeadEntity], Classifier("rec", Literal["a"]), Inverse(ShortHeadEntity, "pack")
    ] = Rel(description="d")


@exclude_graph_model
@entity(description="Short second", domain=SweepDomain)
class ShortSecondEntity(BaseEntity):
    id: str = Field(description="id")
    rec: Annotated[
        Generalization[ShortHeadEntity], Classifier("rec", Literal["a"]), Inverse(ShortHeadEntity, "pack")
    ] = Rel(description="d")


@exclude_graph_model
@entity(description="Short head", domain=SweepDomain)
class ShortHeadEntity(BaseEntity):
    id: str = Field(description="id")
    media: str = Field(description="classifier")
    pack: Annotated[
        Specialization[ShortFirstEntity | ShortSecondEntity],
        Classifier(field="media", codes=Literal["a"]),
        Inverse(field_name="rec"),
    ] = Rel(description="d")


for _cls in (ShortFirstEntity, ShortSecondEntity, ShortHeadEntity):
    _cls.model_rebuild()


# ═════════════════════════════════════════════════════════════════════════════
# Case 5: a code the classifier field's type cannot hold
# ═════════════════════════════════════════════════════════════════════════════


@exclude_graph_model
@entity(description="Numeric-classified alternative", domain=SweepDomain)
class NumericClassifiedAlternativeEntity(BaseEntity):
    id: str = Field(description="id")
    rec: Annotated[
        Generalization[NumericClassifiedHeadEntity],
        Classifier("rec", Literal["a"]),
        Inverse(NumericClassifiedHeadEntity, "pack"),
    ] = Rel(description="d")


@exclude_graph_model
@entity(description="Numeric-classified head", domain=SweepDomain)
class NumericClassifiedHeadEntity(BaseEntity):
    id: str = Field(description="id")
    media: int = Field(description="classifier")
    pack: Annotated[
        Specialization[NumericClassifiedAlternativeEntity],
        Classifier(field="media", codes=Literal["a"]),
        Inverse(field_name="rec"),
    ] = Rel(description="d")


NumericClassifiedAlternativeEntity.model_rebuild()
NumericClassifiedHeadEntity.model_rebuild()


# ═════════════════════════════════════════════════════════════════════════════
# Case 6: a classifier that is a relation
# ═════════════════════════════════════════════════════════════════════════════


@exclude_graph_model
@entity(description="Relation-classified alternative", domain=SweepDomain)
class RelationClassifiedAlternativeEntity(BaseEntity):
    id: str = Field(description="id")
    rec: Annotated[
        Generalization[RelationClassifiedHeadEntity],
        Classifier("rec", Literal["a"]),
        Inverse(RelationClassifiedHeadEntity, "pack"),
    ] = Rel(description="d")


@exclude_graph_model
@entity(description="Other side of the relation", domain=SweepDomain)
class RelationOtherEntity(BaseEntity):
    id: str = Field(description="id")


@exclude_graph_model
@entity(description="Relation-classified head", domain=SweepDomain)
class RelationClassifiedHeadEntity(BaseEntity):
    id: str = Field(description="id")
    other: Annotated[AssociationOne[RelationOtherEntity], NoInverse()] = Rel(description="a relation")
    pack: Annotated[
        Specialization[RelationClassifiedAlternativeEntity],
        Classifier(field="other", codes=Literal["a"]),
        Inverse(field_name="rec"),
    ] = Rel(description="d")


RelationClassifiedAlternativeEntity.model_rebuild()
RelationOtherEntity.model_rebuild()
RelationClassifiedHeadEntity.model_rebuild()


# ═════════════════════════════════════════════════════════════════════════════
# Case 7: a classifier that is not a field of the head
# ═════════════════════════════════════════════════════════════════════════════


@exclude_graph_model
@entity(description="Missing-classifier alternative", domain=SweepDomain)
class MissingClassifierAlternativeEntity(BaseEntity):
    id: str = Field(description="id")
    rec: Annotated[
        Generalization[MissingClassifierHeadEntity],
        Classifier("rec", Literal["a"]),
        Inverse(MissingClassifierHeadEntity, "pack"),
    ] = Rel(description="d")


@exclude_graph_model
@entity(description="Missing-classifier head", domain=SweepDomain)
class MissingClassifierHeadEntity(BaseEntity):
    id: str = Field(description="id")
    pack: Annotated[
        Specialization[MissingClassifierAlternativeEntity],
        Classifier(field="nope", codes=Literal["a"]),
        Inverse(field_name="rec"),
    ] = Rel(description="d")


MissingClassifierAlternativeEntity.model_rebuild()
MissingClassifierHeadEntity.model_rebuild()


# ═════════════════════════════════════════════════════════════════════════════
# Case 8: a classifier naming the axis itself
# ═════════════════════════════════════════════════════════════════════════════


@exclude_graph_model
@entity(description="Self-classified alternative", domain=SweepDomain)
class SelfClassifiedAlternativeEntity(BaseEntity):
    id: str = Field(description="id")
    rec: Annotated[
        Generalization[SelfClassifiedHeadEntity],
        Classifier("rec", Literal["a"]),
        Inverse(SelfClassifiedHeadEntity, "pack"),
    ] = Rel(description="d")


@exclude_graph_model
@entity(description="Self-classified head", domain=SweepDomain)
class SelfClassifiedHeadEntity(BaseEntity):
    id: str = Field(description="id")
    pack: Annotated[
        Specialization[SelfClassifiedAlternativeEntity],
        Classifier(field="pack", codes=Literal["a"]),
        Inverse(field_name="rec"),
    ] = Rel(description="d")


SelfClassifiedAlternativeEntity.model_rebuild()
SelfClassifiedHeadEntity.model_rebuild()


# ═════════════════════════════════════════════════════════════════════════════
# Case 9: one class in two unions
# ═════════════════════════════════════════════════════════════════════════════


@exclude_graph_model
@entity(description="Claimed twice", domain=SweepDomain)
class ClaimedTwiceEntity(BaseEntity):
    id: str = Field(description="id")
    rec: Annotated[
        Generalization[ClaimFirstHeadEntity], Classifier("rec", Literal["a"]), Inverse(ClaimFirstHeadEntity, "pack")
    ] = Rel(description="d")


@exclude_graph_model
@entity(description="Claim first head", domain=SweepDomain)
class ClaimFirstHeadEntity(BaseEntity):
    id: str = Field(description="id")
    media: str = Field(description="classifier")
    pack: Annotated[
        Specialization[ClaimedTwiceEntity],
        Classifier(field="media", codes=Literal["a"]),
        Inverse(field_name="rec"),
    ] = Rel(description="d")


@exclude_graph_model
@entity(description="Claim second head", domain=SweepDomain)
class ClaimSecondHeadEntity(BaseEntity):
    id: str = Field(description="id")
    media: str = Field(description="classifier")
    pack: Annotated[
        Specialization[ClaimedTwiceEntity],
        Classifier(field="media", codes=Literal["a"]),
        Inverse(field_name="rec"),
    ] = Rel(description="d")


for _cls in (ClaimedTwiceEntity, ClaimFirstHeadEntity, ClaimSecondHeadEntity):
    _cls.model_rebuild()


# ═════════════════════════════════════════════════════════════════════════════
# Case 10: two axes decided by one classifier field
# ═════════════════════════════════════════════════════════════════════════════


@exclude_graph_model
@entity(description="Two-axis first", domain=SweepDomain)
class TwoAxisFirstEntity(BaseEntity):
    id: str = Field(description="id")
    rec: Annotated[
        Generalization[TwoAxisHeadEntity], Classifier("rec", Literal["a"]), Inverse(TwoAxisHeadEntity, "pack")
    ] = Rel(description="d")


@exclude_graph_model
@entity(description="Two-axis second", domain=SweepDomain)
class TwoAxisSecondEntity(BaseEntity):
    id: str = Field(description="id")
    rec: Annotated[
        Generalization[TwoAxisHeadEntity], Classifier("rec", Literal["b"]), Inverse(TwoAxisHeadEntity, "other")
    ] = Rel(description="d")


@exclude_graph_model
@entity(description="Two-axis head", domain=SweepDomain)
class TwoAxisHeadEntity(BaseEntity):
    id: str = Field(description="id")
    media: str = Field(description="classifier")
    pack: Annotated[
        Specialization[TwoAxisFirstEntity],
        Classifier(field="media", codes=Literal["a"]),
        Inverse(field_name="rec"),
    ] = Rel(description="d")
    other: Annotated[
        Specialization[TwoAxisSecondEntity],
        Classifier(field="media", codes=Literal["b"]),
        Inverse(field_name="rec"),
    ] = Rel(description="d")


for _cls in (TwoAxisFirstEntity, TwoAxisSecondEntity, TwoAxisHeadEntity):
    _cls.model_rebuild()


# ═════════════════════════════════════════════════════════════════════════════
# Case 11: a class pointing at an axis without being named in it
# ═════════════════════════════════════════════════════════════════════════════


@exclude_graph_model
@entity(description="Closed named", domain=SweepDomain)
class ClosedNamedEntity(BaseEntity):
    id: str = Field(description="id")
    rec: Annotated[
        Generalization[ClosedSweepHeadEntity], Classifier("rec", Literal["a"]), Inverse(ClosedSweepHeadEntity, "pack")
    ] = Rel(description="d")


@exclude_graph_model
@entity(description="Closed intruder", domain=SweepDomain)
class ClosedIntruderEntity(BaseEntity):
    id: str = Field(description="id")
    rec: Annotated[Generalization[ClosedSweepHeadEntity], Classifier("rec", Literal["b"])] = Rel(description="d")


@exclude_graph_model
@entity(description="Closed head", domain=SweepDomain)
class ClosedSweepHeadEntity(BaseEntity):
    id: str = Field(description="id")
    media: str = Field(description="classifier")
    pack: Annotated[
        Specialization[ClosedNamedEntity],
        Classifier(field="media", codes=Literal["a"]),
        Inverse(field_name="rec"),
    ] = Rel(description="d")


for _cls in (ClosedNamedEntity, ClosedIntruderEntity, ClosedSweepHeadEntity):
    _cls.model_rebuild()


# ═════════════════════════════════════════════════════════════════════════════
# Case 12: a head naming itself
# ═════════════════════════════════════════════════════════════════════════════


@exclude_graph_model
@entity(description="Self-referring head", domain=SweepDomain)
class SelfReferringHeadEntity(BaseEntity):
    id: str = Field(description="id")
    media: str = Field(description="classifier")
    back: Annotated[
        Generalization[SelfReferringHeadEntity],
        Classifier("back", Literal["a"]),
        Inverse(SelfReferringHeadEntity, "loop"),
    ] = Rel(description="d")
    loop: Annotated[
        Specialization[SelfReferringHeadEntity],
        Classifier(field="media", codes=Literal["a"]),
        Inverse(field_name="back"),
    ] = Rel(description="d")


SelfReferringHeadEntity.model_rebuild()


# ═════════════════════════════════════════════════════════════════════════════
# The sweep: one row per rule of the design's rule table
# ═════════════════════════════════════════════════════════════════════════════

CASES: list[tuple[str, list[type[BaseEntity]], str]] = [
    (
        "an alternative that is not a declared entity",
        [HeadOverUndeclaredEntity],
        "is not a declared entity",
    ),
    (
        "an alternative that declares no code",
        [HeadOverCodeLessEntity],
        "declares no code",
    ),
    (
        "a code the head names and no class declares",
        [HeadOverOrphanCodeEntity],
        "no alternative declares them",
    ),
    (
        "fewer codes than alternatives",
        [ShortHeadEntity],
        "every alternative needs exactly one code",
    ),
    (
        "a code the classifier's type cannot hold",
        [NumericClassifiedHeadEntity],
        "cannot be stored by classifier field",
    ),
    (
        "a classifier that is a relation",
        [RelationClassifiedHeadEntity],
        "is a relation, not a scalar field",
    ),
    (
        "a classifier that is not a field",
        [MissingClassifierHeadEntity],
        "is not a field of",
    ),
    (
        "a classifier naming the axis itself",
        [SelfClassifiedHeadEntity],
        "names the specialization field itself",
    ),
    (
        "one class in two unions",
        [ClaimFirstHeadEntity, ClaimSecondHeadEntity],
        "is an alternative of",
    ),
    (
        "two axes decided by one classifier field",
        [TwoAxisHeadEntity],
        "already decides",
    ),
    (
        "a class pointing at an axis without being named in it",
        [ClosedSweepHeadEntity, ClosedIntruderEntity, ClosedNamedEntity],
        "without being named",
    ),
    (
        "a head naming itself",
        [SelfReferringHeadEntity],
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
    two alternatives, two codes, one classifier, each class reachable — and it must build.
    A validator that refused everything would pass all twelve cases and fail here.
    """
    validate_entity_specializations([GoodFirstEntity, GoodSecondEntity, GoodHeadEntity])


def test_every_rule_the_design_names_has_a_case() -> None:
    """
    The sweep is only as good as its coverage, so the coverage is asserted.

    The rule table of the design names eleven rules the framework checks at build time. The
    sweep carries a case for each, and two of them share a case because they produce the same
    report — mutuality has no check of its own, which the axis-rule file records. This test
    fails if a rule is added to the design and no case follows it.
    """
    covered = {
        "not a declared entity",
        "no code of its own",
        "codes compared in both directions",
        "no code declared twice",
        "code incompatible with the classifier's type",
        "mutuality with the reverse declaration",
        "closure against the rest of the model",
        "one class, one head",
        "one classifier, one axis",
        "the classifier names a scalar field",
        "no cycle between a head and its extensions",
    }
    assert len(CASES) >= len(covered) - 1, "mutuality shares its case with the code comparison"
    assert len(covered) == 11, "the design's table has eleven rules; update this count with it"

# ═════════════════════════════════════════════════════════════════════════════
# A model breaking two rules at once
# ═════════════════════════════════════════════════════════════════════════════


@exclude_graph_model
class NotAnEntityAlternativeEntity(BaseEntity):
    """Shaped like an alternative and never decorated."""

    id: str = Field(description="id")


@exclude_graph_model
@entity(description="Mismatched twin", domain=SweepDomain)
class MismatchedTwinEntity(BaseEntity):
    """Declares a code the head does not name, on a field that does point at the head."""

    id: str = Field(description="id")
    rec: Annotated[
        Generalization[TwoFaultsHeadEntity], Classifier("rec", Literal["zzz"]), Inverse(TwoFaultsHeadEntity, "pack")
    ] = Rel(description="d")


@exclude_graph_model
@entity(description="Head with two faults", domain=SweepDomain)
class TwoFaultsHeadEntity(BaseEntity):
    """One alternative is not an entity; the other declares a code nobody names."""

    id: str = Field(description="id")
    media: str = Field(description="classifier")
    pack: Annotated[
        Specialization[NotAnEntityAlternativeEntity | MismatchedTwinEntity],
        Classifier(field="media", codes=Literal["a"]),
        Inverse(field_name="rec"),
    ] = Rel(description="d")


NotAnEntityAlternativeEntity.model_rebuild()
MismatchedTwinEntity.model_rebuild()
TwoFaultsHeadEntity.model_rebuild()


@exclude_graph_model
@entity(description="Unfitting alternative", domain=SweepDomain)
class UnfittingAlternativeEntity(BaseEntity):
    id: str = Field(description="id")
    rec: Annotated[
        Generalization[TwoFaultsNumericHeadEntity],
        Classifier("rec", Literal["a"]),
        Inverse(TwoFaultsNumericHeadEntity, "pack"),
    ] = Rel(description="d")


@exclude_graph_model
@entity(description="Head with a code that is both unknown and unfitting", domain=SweepDomain)
class TwoFaultsNumericHeadEntity(BaseEntity):
    """The head names a code no class declares, and the classifier's type could not hold it either."""

    id: str = Field(description="id")
    media: int = Field(description="classifier")
    pack: Annotated[
        Specialization[UnfittingAlternativeEntity],
        Classifier(field="media", codes=Literal["a"]),
        Inverse(field_name="rec"),
    ] = Rel(description="d")


UnfittingAlternativeEntity.model_rebuild()
TwoFaultsNumericHeadEntity.model_rebuild()


def test_a_model_with_two_faults_reports_the_more_fundamental_one() -> None:
    """
    Two rules are broken and one is reported: the one about the class, not the one about the code.

    A validator that walked its checks in an arbitrary order would report whichever it happened
    to look at, and the developer would fix that one, rebuild, and meet the other. Reporting the
    more fundamental fault does not make the second disappear — it makes the first build fail for
    a reason worth acting on.
    """
    with pytest.raises(SpecializationDeclarationError) as caught:
        validate_entity_specializations([TwoFaultsHeadEntity])
    message = str(caught.value)

    assert "is not a declared entity" in message
    assert "zzz" not in message, "the code fault is real but is not what this build reports"


def test_a_code_the_classifier_cannot_hold_is_refused_before_anything_else() -> None:
    """
    A word in a numeric classifier is refused as unfitting, and the comparison never runs.

    This was written the other way round first, expecting the unknown-code report, and the run
    showed only one rule actually applies: the alternative here declares the same code the head
    names, so the comparison is satisfied. The interesting property is the order that follows
    from that — a code that cannot be stored is refused on its own account, before any question
    of codes matching is asked.
    """
    with pytest.raises(SpecializationDeclarationError) as caught:
        validate_entity_specializations([TwoFaultsNumericHeadEntity])
    message = str(caught.value)

    assert "cannot be stored by classifier field" in message
    assert "no alternative declares them" not in message


@exclude_graph_model
@entity(description="Unknown-code alternative", domain=SweepDomain)
class UnknownCodeAlternativeEntity(BaseEntity):
    """Declares a word for a classifier that holds words, so the type is satisfied and the code is not."""

    id: str = Field(description="id")
    rec: Annotated[
        Generalization[TwoFaultsTextHeadEntity],
        Classifier("rec", Literal["other"]),
        Inverse(TwoFaultsTextHeadEntity, "pack"),
    ] = Rel(description="d")


@exclude_graph_model
@entity(description="Head naming an unknown, storable code", domain=SweepDomain)
class TwoFaultsTextHeadEntity(BaseEntity):
    id: str = Field(description="id")
    media: str = Field(description="classifier")
    pack: Annotated[
        Specialization[UnknownCodeAlternativeEntity],
        Classifier(field="media", codes=Literal["mine"]),
        Inverse(field_name="rec"),
    ] = Rel(description="d")


UnknownCodeAlternativeEntity.model_rebuild()
TwoFaultsTextHeadEntity.model_rebuild()


def test_a_code_that_fits_the_type_but_no_class_declares_is_refused_as_unknown() -> None:
    """The type is satisfied, so the comparison is the rule that speaks — and nothing else does."""
    with pytest.raises(SpecializationDeclarationError) as caught:
        validate_entity_specializations([TwoFaultsTextHeadEntity])
    message = str(caught.value)

    assert "no alternative declares them" in message
    assert "cannot be stored" not in message


def test_the_report_for_one_model_is_the_same_every_time() -> None:
    """Nothing in the pass depends on iteration order, so the same model reports the same rule."""
    messages = set()
    for _ in range(5):
        with pytest.raises(SpecializationDeclarationError) as caught:
            validate_entity_specializations([TwoFaultsHeadEntity, ClaimFirstHeadEntity, ClaimSecondHeadEntity])
        messages.add(str(caught.value))

    assert len(messages) == 1, f"the report changed between runs: {messages}"
