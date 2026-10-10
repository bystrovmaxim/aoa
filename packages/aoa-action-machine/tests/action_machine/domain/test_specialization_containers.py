# tests/action_machine/domain/test_specialization_containers.py
"""
Tests for the specialization **containers** and their marker.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A head field points at one of N extension entities. The alternatives live in the
container's **type argument** — ``Specialization[A | B]`` — and what selects among
them lives in the ``Classifier`` marker beside it. These tests assert what the type
argument buys and what the marker promises:

- subscripting a container produces a real class, so a field of that type accepts an
  instance of it;
- the type argument is enforced: a narrower parameterisation refuses the other
  alternatives, and a class outside the union is refused on assignment;
- a link whose row was not loaded keeps its identifier and its variant — the state a
  bare union in the type position could not express;
- printing a head and its extension terminates, although they reference each other;
- both containers are frozen, and the marker keeps one entry per kind of mistake.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- **ValidationError** — an assignment the type argument refuses, or a mutation of a
  frozen container.
- **TypeError** / **ValueError** — a wrong or empty argument to ``Classifier``.
- **AttributeError** — assigning to a frozen marker.

Does not cover parsing, the graph, or the build rules — only the types themselves.
"""

from typing import Any, Literal

import pytest
from pydantic import BaseModel, Field, ValidationError

from aoa.action_machine.domain import Classifier, Generalization, Specialization


class FirstEntity(BaseModel):
    """A stand-in extension: the tests never need a real ``@entity``."""

    id: str = Field(description="id")
    stamper: str = Field(description="a column of its own")


class SecondEntity(BaseModel):
    """A second stand-in extension, deliberately of the same shape."""

    id: str = Field(description="id")
    year: int = Field(description="a column of its own")


class OutsideEntity(BaseModel):
    """A class the unions below never name."""

    id: str = Field(description="id")


class _Head(BaseModel):
    """A head whose field carries the union under test."""

    id: str = Field(description="id")
    link: Specialization[FirstEntity | SecondEntity] | None = Field(default=None, description="one of two")


# ─────────────────────────────────────────────────────────────────────────────
# The type argument is a real class, and it is enforced
# ─────────────────────────────────────────────────────────────────────────────


def test_subscription_produces_a_real_class() -> None:
    alias = Specialization[FirstEntity | SecondEntity]
    assert isinstance(alias, type)
    instance = alias(id="x", variant="first")
    assert instance.id == "x"
    assert instance.variant == "first"
    assert instance.entity is None


def test_a_member_of_the_union_is_accepted() -> None:
    head = _Head(id="h", link=Specialization[FirstEntity | SecondEntity](id="x", variant="first", entity=FirstEntity(id="x", stamper="1A")))
    assert isinstance(head.link, Specialization)
    assert isinstance(head.link.entity, FirstEntity)


def test_a_class_outside_the_union_is_refused() -> None:
    with pytest.raises(ValidationError):
        _Head(
            id="h",
            link=Specialization[FirstEntity | SecondEntity](id="x", variant="v", entity=OutsideEntity(id="x")),
        )


def test_a_narrower_parameterisation_refuses_the_other_member() -> None:
    narrow = Specialization[FirstEntity]
    accepted = narrow(id="x", variant="first", entity=FirstEntity(id="x", stamper="1A"))
    assert isinstance(accepted.entity, FirstEntity)

    with pytest.raises(ValidationError):
        narrow(id="x", variant="second", entity=SecondEntity(id="x", year=1997))


def test_a_plain_string_is_refused_where_a_row_is_expected() -> None:
    with pytest.raises(ValidationError):
        Specialization[FirstEntity](id="x", variant="first", entity="not a row")


# ─────────────────────────────────────────────────────────────────────────────
# A link without a loaded row: the state a bare union could not express
# ─────────────────────────────────────────────────────────────────────────────


def test_an_unloaded_link_keeps_its_identifier_and_variant() -> None:
    link = Specialization[FirstEntity | SecondEntity](id="rec-9", variant="test")
    head = _Head(id="h", link=link)

    assert head.link.id == "rec-9"
    assert head.link.variant == "test"
    assert head.link.entity is None


def test_the_extension_side_carries_its_identifier() -> None:
    back = Generalization[FirstEntity](id="rec-1")
    assert back.id == "rec-1"
    assert back.entity is None

    hydrated = Generalization[FirstEntity](id="rec-1", entity=FirstEntity(id="rec-1", stamper="1A"))
    assert isinstance(hydrated.entity, FirstEntity)


def test_the_extension_side_refuses_another_class() -> None:
    with pytest.raises(ValidationError):
        Generalization[FirstEntity](id="rec-1", entity=SecondEntity(id="rec-1", year=1997))


# ─────────────────────────────────────────────────────────────────────────────
# Mutually referencing rows print, and the containers do not change
# ─────────────────────────────────────────────────────────────────────────────


def test_repr_of_a_mutually_referencing_pair_terminates() -> None:
    head = _Head(id="h")
    link = Specialization[FirstEntity | SecondEntity](id="h", variant="first", entity=FirstEntity(id="h", stamper="1A"))
    head.link = link

    text = repr(head)
    assert "Specialization" in text
    assert text.count("FirstEntity") <= 1, "the row inside must not be printed, or the pair recurses"


def test_both_containers_are_frozen() -> None:
    link = Specialization[FirstEntity | SecondEntity](id="x", variant="first")
    with pytest.raises(ValidationError):
        link.variant = "second"

    back = Generalization[FirstEntity](id="x")
    with pytest.raises(ValidationError):
        back.id = "y"


# ─────────────────────────────────────────────────────────────────────────────
# The marker: two named arguments, one entry per kind of mistake
# ─────────────────────────────────────────────────────────────────────────────


def test_classifier_exposes_the_literal_and_plain_codes() -> None:
    marker = Classifier(field="media", codes=Literal["first", "repress", "test"])

    assert marker.field == "media"
    assert marker.code_values == ("first", "repress", "test")
    assert marker.codes == Literal["first", "repress", "test"]


def test_classifier_declaration_order_is_kept() -> None:
    marker = Classifier(field="media", codes=Literal["repress", "first"])
    assert marker.code_values == ("repress", "first")


def test_classifier_is_frozen() -> None:
    marker = Classifier(field="media", codes=Literal["first"])
    with pytest.raises(AttributeError):
        marker.field = "other"


def test_classifier_equality_follows_its_arguments() -> None:
    same = Classifier(field="media", codes=Literal["first", "repress"])
    other = Classifier(field="media", codes=Literal["first", "repress"])
    different = Classifier(field="channel", codes=Literal["first", "repress"])

    assert same == other
    assert hash(same) == hash(other)
    assert same != different


def test_classifier_refuses_a_missing_or_empty_field_name() -> None:
    with pytest.raises(TypeError):
        Classifier(field=123, codes=Literal["first"])  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        Classifier(field="   ", codes=Literal["first"])


def test_classifier_refuses_codes_that_are_not_a_literal() -> None:
    with pytest.raises(TypeError):
        Classifier(field="media", codes="first")  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        Classifier(field="media", codes=("first",))  # type: ignore[arg-type]


def test_classifier_refuses_an_empty_literal() -> None:
    with pytest.raises(ValueError):
        Classifier(field="media", codes=Literal[()])


def test_classifier_refuses_a_non_string_code() -> None:
    with pytest.raises(TypeError):
        Classifier(field="media", codes=Literal[1])  # type: ignore[arg-type]


def test_classifier_refuses_an_empty_code() -> None:
    with pytest.raises(ValueError):
        Classifier(field="media", codes=Literal["first", "   "])


def test_classifier_repr_names_both_arguments() -> None:
    marker = Classifier(field="media", codes=Literal["first"])
    assert repr(marker) == "Classifier(field='media', codes=typing.Literal['first'])"


def test_the_marker_keeps_the_argument_it_was_given() -> None:
    codes: Any = Literal["first", "repress"]
    marker = Classifier(field="media", codes=codes)
    assert marker.codes is codes
