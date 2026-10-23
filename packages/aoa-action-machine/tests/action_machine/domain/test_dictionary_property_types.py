# tests/action_machine/domain/test_dictionary_property_types.py
"""
Tests for the property types a dictionary value may declare.

A dictionary value is shared by every consumer, so its extra fields are limited
to immutable types: a list or a mapping would be reachable through
``to_reference()`` and through the declared attribute. The rule binds the
dictionary kind only — a lifecycle status keeps the freedom its own suite relies
on, because a status may carry data that need not be hashable.
"""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
from typing import Any, Literal
from uuid import UUID

import pytest
from pydantic import BaseModel, Field, field_validator

from aoa.action_machine.domain import BaseEnumEntity, BaseStateEntity, value

_ACCEPTED = (
    ("text", str, "value"),
    ("count", int, 1),
    ("ratio", float, 1.5),
    ("flag", bool, True),
    ("amount", Decimal, Decimal("9.99")),
    ("day", date, date(2020, 1, 2)),
    ("moment", datetime, datetime(2020, 1, 2, 3, 4)),
    ("clock", time, time(3, 4)),
    ("key", UUID, UUID(int=0)),
)

_REFUSED = (
    ("labels", list[str], "list"),
    ("amounts", dict[str, int], "dict"),
    ("tags", set[str], "set"),
    ("frozen", frozenset[str], "frozenset"),
)


class Grade(Enum):
    """An enum is immutable and therefore supported."""

    A = "a"


class Nested(BaseModel):
    """A nested model is mutable through its own containers, so it is refused."""

    amount: int = Field(default=0, description="An amount")


def _build(**namespace: object) -> type[BaseEnumEntity]:
    """Build a graph-excluded dictionary class with the given class-body namespace."""
    return type("ProbeEnumEntity", (BaseEnumEntity,), {"__graph_exclude_graph_model__": True, **namespace})


@pytest.mark.parametrize(("name", "annotation", "sample"), _ACCEPTED)
def test_an_immutable_leaf_type_is_accepted(name: str, annotation: type, sample: object) -> None:
    """Every supported leaf type declares a value and keeps it unchanged."""
    probe = _build(**{"__annotations__": {name: annotation}, "V": value(code="v", display_name="V", **{name: sample})})
    assert probe.codes() == ["v"]
    assert getattr(probe.V, name) == sample


def test_an_enum_literal_tuple_and_optional_are_accepted() -> None:
    """An enum, a Literal, a tuple of supported values and an Optional are all supported."""
    probe = _build(
        **{
            "__annotations__": {
                "grade": Grade,
                "size": Literal["small", "large"],
                "tags": tuple[str, ...],
                "note": str | None,
            },
            "V": value(code="v", display_name="V", grade=Grade.A, size="small", tags=("a", "b"), note=None),
        }
    )
    assert probe.V.tags == ("a", "b")
    assert probe.V.note is None


@pytest.mark.parametrize(("name", "annotation", "refused"), _REFUSED)
def test_a_mutable_container_is_refused(name: str, annotation: type, refused: str) -> None:
    """A mutable container is refused at class creation, naming the class, the field and the type."""
    with pytest.raises(ValueError, match=rf"ProbeEnumEntity: field '{name}' is {refused}"):
        _build(**{"__annotations__": {name: annotation}, "V": value(code="v", display_name="V")})


def test_a_nested_model_is_refused() -> None:
    """A nested model cannot be promised immutable, so it is refused."""
    with pytest.raises(ValueError, match="field 'detail' is Nested"):
        _build(**{"__annotations__": {"detail": Nested}, "V": value(code="v", display_name="V")})


def test_a_bare_any_is_refused() -> None:
    """A value whose type cannot be classified cannot be promised immutable."""
    with pytest.raises(ValueError, match="field 'payload' is Any"):
        _build(**{"__annotations__": {"payload": Any}, "V": value(code="v", display_name="V")})


def test_a_mutable_container_nested_in_a_supported_one_is_refused() -> None:
    """The rule is recursive: a tuple that holds a list is refused like the list itself."""
    with pytest.raises(ValueError, match="field 'rows' is list"):
        _build(**{"__annotations__": {"rows": tuple[list[str], ...]}, "V": value(code="v", display_name="V")})


def test_a_mutable_container_inside_an_optional_is_refused() -> None:
    """Optional does not hide a refused type."""
    with pytest.raises(ValueError, match="field 'labels' is list"):
        _build(**{"__annotations__": {"labels": list[str] | None}, "V": value(code="v", display_name="V")})


def test_a_state_type_keeps_its_mutable_properties() -> None:
    """The rule binds the dictionary kind; a status may still carry what its suite relies on."""
    probe = type(
        "FreeStateEntity",
        (BaseStateEntity,),
        {
            "__annotations__": {"labels": list[str]},
            "L": value(code="free", display_name="Free", labels=["original"]),
        },
    )
    assert probe.codes() == ["free"]
    assert probe.L.labels == ["original"]

def test_a_validator_that_returns_a_list_is_refused_before_publication() -> None:
    """The completed member is checked, not only its annotation."""
    with pytest.raises(ValueError, match=r"property 'labels'.*holds list.*tuple\[str, \.\.\.\]"):
        class LabelsEnumEntity(BaseEnumEntity):
            """Declare labels shared by all users of this value."""

            labels: tuple[str, ...]

            ITEM = value(code="item", display_name="Item", labels=("original",))

            @field_validator("labels", mode="after")
            @classmethod
            def replace_with_list(cls, labels: tuple[str, ...]) -> list[str]:
                """Return a list, violating the property contract."""
                return list(labels)


def test_a_validator_that_returns_another_immutable_type_is_refused() -> None:
    """An immutable value of the wrong shape contradicts the schema the dictionary publishes."""
    with pytest.raises(ValueError, match=r"property 'labels'.*holds str.*tuple\[str, \.\.\.\]"):
        class ShapeEnumEntity(BaseEnumEntity):
            """Declare a tuple property."""

            labels: tuple[str, ...]

            ITEM = value(code="item", display_name="Item", labels=("a",))

            @field_validator("labels", mode="after")
            @classmethod
            def join(cls, labels: tuple[str, ...]) -> str:
                """Return a different immutable type."""
                return ",".join(labels)


def test_a_list_nested_inside_a_tuple_is_refused() -> None:
    """The runtime check is recursive, like the annotation check."""
    with pytest.raises(ValueError, match=r"labels\[1\].*list"):
        class NestedEnumEntity(BaseEnumEntity):
            """Declare a tuple property whose validator hides a list inside it."""

            labels: tuple[str, ...]

            ITEM = value(code="item", display_name="Item", labels=("a",))

            @field_validator("labels", mode="after")
            @classmethod
            def hide_a_list(cls, labels: tuple[str, ...]) -> tuple[object, ...]:
                """Return a tuple holding a mutable value."""
                return ("a", ["b"])


def test_an_enum_with_a_mutable_value_is_refused() -> None:
    """Accepting the annotation alone does not establish that the value is immutable."""
    class Flags(Enum):
        """Name the flags."""

        X = ["a", "b"]

    with pytest.raises(ValueError, match=r"property 'flags'.*Flags.*list"):
        class FlagsEnumEntity(BaseEnumEntity):
            """Carry an enum property whose value is a list."""

            flags: Flags

            ITEM = value(code="item", display_name="Item", flags=Flags.X)


def test_a_validator_that_returns_an_equal_tuple_publishes_the_member() -> None:
    """A valid immutable result keeps working, including export independence."""
    class CopyEnumEntity(BaseEnumEntity):
        """Declare a tuple property a validator rebuilds."""

        labels: tuple[str, ...]

        ITEM = value(code="item", display_name="Item", labels=("original",))

        @field_validator("labels", mode="after")
        @classmethod
        def rebuild(cls, labels: tuple[str, ...]) -> tuple[str, ...]:
            """Return an equal tuple."""
            return tuple(labels)

    assert CopyEnumEntity.by_code("item").labels == ("original",)

    exported = CopyEnumEntity.ITEM.to_reference()
    exported["properties"]["labels"].append("changed")
    assert CopyEnumEntity.ITEM.labels == ("original",)
    assert CopyEnumEntity.by_code("item").to_reference()["properties"]["labels"] == ["original"]
