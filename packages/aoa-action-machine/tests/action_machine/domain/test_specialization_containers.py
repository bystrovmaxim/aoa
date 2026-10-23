# tests/action_machine/domain/test_specialization_containers.py
"""
The container types themselves: ``Specialization[Alternatives, Dictionary]`` and ``Generalization[Head]``.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A field's type argument is a declaration, and these tests are what it actually enforces
at assignment time: which class may sit in ``entity``, what ``variant`` may hold, and what
the container refuses outright. The dictionary is part of the type: a container names it,
and its ``variant`` carries one of that dictionary's values — not a bare code, not a copy,
not a value of some other dictionary.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- **ValidationError** — the assignment the type refuses.

Does not cover parsing, the graph, or the build rules — only the types themselves. The
marker's code-list form is gone with the classifier field, so the tests that exercised it
are gone too; what remains is the value form.
"""

from __future__ import annotations

from typing import Annotated, Any

import pytest
from pydantic import BaseModel, Field, ValidationError

from aoa.action_machine.domain import BaseEnumEntity, Classifier, Generalization, Specialization, value
from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model


@exclude_graph_model
class KindEnumEntity(BaseEnumEntity):
    """The dictionary the container borrows its values from."""

    FIRST = value(code="first", display_name="First")
    SECOND = value(code="second", display_name="Second")


class FirstEntity(BaseModel):
    """A stand-in extension: the tests never need a real ``@entity``."""

    id: str = Field(description="id")
    stamper: str = Field(description="a column of its own")
    marker: Annotated[Any, Classifier(field="marker", variant=KindEnumEntity.FIRST)] = Field(
        default=None, description="names this class's value"
    )


class SecondEntity(BaseModel):
    """A second stand-in extension, deliberately of the same shape."""

    id: str = Field(description="id")
    year: int = Field(description="a column of its own")
    marker: Annotated[Any, Classifier(field="marker", variant=KindEnumEntity.SECOND)] = Field(
        default=None, description="names this class's value"
    )


class OutsideEntity(BaseModel):
    """A class the unions below never name."""

    id: str = Field(description="id")


class _Head(BaseModel):
    """A head whose field carries the union under test."""

    id: str = Field(description="id")
    link: Specialization[FirstEntity | SecondEntity, KindEnumEntity] | None = Field(
        default=None, description="one of two"
    )


# ─────────────────────────────────────────────────────────────────────────────
# The type argument is a real class, and it is enforced
# ─────────────────────────────────────────────────────────────────────────────


def test_subscription_produces_a_real_class() -> None:
    """A container is a class, not a typing alias: it can be assigned and validated."""
    alias = Specialization[FirstEntity | SecondEntity, KindEnumEntity]

    assert isinstance(alias, type)
    assert alias.model_fields["variant"].annotation is KindEnumEntity


def test_a_member_of_the_union_is_accepted() -> None:
    """The class named in the union is what ``entity`` may hold."""
    head = _Head(
        id="h",
        link=Specialization[FirstEntity | SecondEntity, KindEnumEntity](
            id="x", variant=KindEnumEntity.FIRST, entity=FirstEntity(id="x", stamper="1A")
        ),
    )

    assert head.link is not None
    assert isinstance(head.link.entity, FirstEntity)


def test_a_class_outside_the_union_is_refused() -> None:
    """A class the union never named is not a member."""
    with pytest.raises(ValidationError):
        _Head(
            id="h",
            link=Specialization[FirstEntity | SecondEntity, KindEnumEntity](
                id="x", variant=KindEnumEntity.FIRST, entity=OutsideEntity(id="x")
            ),
        )


def test_a_narrower_parameterisation_refuses_the_other_member() -> None:
    """One alternative in the union means the other class is not a member."""
    narrow = Specialization[FirstEntity, KindEnumEntity]

    with pytest.raises(ValidationError):
        narrow(id="x", variant=KindEnumEntity.FIRST, entity=SecondEntity(id="x", year=1997))


def test_a_plain_string_is_refused_where_a_row_is_expected() -> None:
    """``entity`` holds a row or nothing."""
    with pytest.raises(ValidationError):
        Specialization[FirstEntity, KindEnumEntity](id="x", variant=KindEnumEntity.FIRST, entity="not a row")


def test_an_unloaded_link_keeps_its_identifier_and_variant() -> None:
    """A link may be known without its row; the value still says which one it is."""
    link = Specialization[FirstEntity | SecondEntity, KindEnumEntity](id="rec-9", variant=KindEnumEntity.SECOND)

    assert link.id == "rec-9"
    assert link.variant is KindEnumEntity.SECOND
    assert link.entity is None


def test_the_extension_side_carries_its_identifier() -> None:
    """The reverse container holds the head's id, and the row when it is loaded."""
    reverse = Generalization[_Head](id="h", entity=_Head(id="h"))

    assert reverse.id == "h"
    assert isinstance(reverse.entity, _Head)


def test_the_extension_side_refuses_another_class() -> None:
    """The reverse container names its head, so nothing else fits."""
    with pytest.raises(ValidationError):
        Generalization[_Head](id="h", entity=FirstEntity(id="h", stamper="1A"))


def test_repr_of_a_mutually_referencing_pair_terminates() -> None:
    """The pair points at each other; its repr must not follow the loop."""
    link = Specialization[FirstEntity | SecondEntity, KindEnumEntity](
        id="h", variant=KindEnumEntity.FIRST, entity=FirstEntity(id="h", stamper="1A")
    )
    reverse = Generalization[_Head](id="h", entity=_Head(id="h", link=link))

    assert "FirstEntity" in repr(link)
    assert repr(reverse) == "Generalization[_Head](id='h')", "the row is left out of the repr, so it terminates"


def test_both_containers_are_frozen() -> None:
    """A link is a value: assigning to it is refused."""
    link = Specialization[FirstEntity | SecondEntity, KindEnumEntity](id="x", variant=KindEnumEntity.FIRST)

    with pytest.raises(ValidationError):
        link.id = "y"  # type: ignore[misc]


# ─────────────────────────────────────────────────────────────────────────────
# The variant is a value of the dictionary
# ─────────────────────────────────────────────────────────────────────────────


def test_the_variant_holds_the_declared_value() -> None:
    """A declared value passes by identity."""
    link = Specialization[FirstEntity | SecondEntity, KindEnumEntity](id="x", variant=KindEnumEntity.SECOND)

    assert link.variant is KindEnumEntity.SECOND


def test_the_variant_refuses_a_bare_code() -> None:
    """The resource resolves a stored code before the model sees it."""
    with pytest.raises(ValidationError, match="bare code is not accepted"):
        Specialization[FirstEntity | SecondEntity, KindEnumEntity](id="x", variant="second")


def test_the_variant_refuses_an_undeclared_code() -> None:
    """The dictionary in the type argument is the closed set."""
    with pytest.raises(ValidationError, match="is not a declared value"):
        Specialization[FirstEntity | SecondEntity, KindEnumEntity](id="x", variant={"code": "elsewhere"})


def test_the_variant_serializes_as_the_reference_object() -> None:
    """The wire carries the value whole."""
    link = Specialization[FirstEntity | SecondEntity, KindEnumEntity](id="x", variant=KindEnumEntity.FIRST)

    assert link.model_dump()["variant"] == {"code": "first", "display_name": "First", "properties": {}}


def test_a_mismatched_pair_is_refused() -> None:
    """The value and the class of the loaded row must agree."""
    with pytest.raises(ValidationError, match="does not match"):
        Specialization[FirstEntity | SecondEntity, KindEnumEntity](
            id="x", variant=KindEnumEntity.FIRST, entity=SecondEntity(id="x", year=1997)
        )


def test_classifier_names_one_value_and_stays_frozen() -> None:
    """The extension's marker names a value and cannot be edited afterwards."""
    marker = Classifier(field="record", variant=KindEnumEntity.FIRST)

    assert marker.variant is KindEnumEntity.FIRST
    assert marker.field == "record"
    with pytest.raises(AttributeError):
        marker.field = "other"  # type: ignore[misc]


def test_classifier_refuses_a_list_of_codes() -> None:
    """A code list is not a value: the marker refuses it outright."""
    with pytest.raises(TypeError, match=r"must be a declared dictionary value"):
        Classifier("media", ["first"])
