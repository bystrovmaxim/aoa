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


def test_a_literal_result_outside_the_choices_is_refused() -> None:
    """A supported scalar is not enough: it must be one of the declared choices."""
    with pytest.raises(
        ValueError,
        match=r"LiteralEnumEntity: the property 'choice' of member 'ITEM' holds str \(expected Literal\['a'\]\)",
    ):

        class LiteralEnumEntity(BaseEnumEntity):
            """Declare one permitted choice."""

            choice: Literal["a"]

            ITEM = value(code="item", display_name="Item", choice="a")

            @field_validator("choice", mode="after")
            @classmethod
            def replace(cls, choice: str) -> str:
                """Return a scalar outside the permitted choices."""
                return "b"


def test_a_literal_result_inside_the_choices_publishes_the_member() -> None:
    """The neighbour of the refusal: another permitted choice is published unchanged."""

    class OtherLiteralEnumEntity(BaseEnumEntity):
        """Declare two permitted choices."""

        choice: Literal["a", "b"]

        ITEM = value(code="item", display_name="Item", choice="a")

        @field_validator("choice", mode="after")
        @classmethod
        def replace(cls, choice: str) -> str:
            """Return the second permitted choice."""
            return "b"

    assert OtherLiteralEnumEntity.ITEM.choice == "b"


def test_none_is_refused_for_a_non_nullable_union() -> None:
    """A union of several types does not permit null by itself."""
    with pytest.raises(
        ValueError,
        match=r"UnionEnumEntity: the property 'choice' of member 'ITEM' holds NoneType \(expected str \| int\)",
    ):

        class UnionEnumEntity(BaseEnumEntity):
            """Declare a union without null."""

            choice: str | int

            ITEM = value(code="item", display_name="Item", choice="a")

            @field_validator("choice", mode="after")
            @classmethod
            def replace(cls, choice: str | int) -> None:
                """Return null although the annotation excludes it."""
                return None


def test_a_union_member_publishes_the_member() -> None:
    """The neighbour of the null refusal: a declared member type is accepted."""

    class MemberUnionEnumEntity(BaseEnumEntity):
        """Declare a union without null."""

        choice: str | int

        ITEM = value(code="item", display_name="Item", choice="a")

        @field_validator("choice", mode="after")
        @classmethod
        def replace(cls, choice: str | int) -> int:
            """Return the other declared member type."""
            return 10

    assert MemberUnionEnumEntity.ITEM.choice == 10


def test_none_is_accepted_for_a_nullable_union() -> None:
    """Null is accepted when the union names it."""

    class NullableUnionEnumEntity(BaseEnumEntity):
        """Declare a union that includes null."""

        choice: str | int | None

        ITEM = value(code="item", display_name="Item", choice="a")

        @field_validator("choice", mode="after")
        @classmethod
        def replace(cls, choice: str | int | None) -> None:
            """Return the null the annotation permits."""
            return None

    assert NullableUnionEnumEntity.ITEM.choice is None


def test_a_literal_outside_the_choices_is_refused_inside_a_tuple() -> None:
    """The literal rule reaches a tuple item and the path names its index."""
    with pytest.raises(
        ValueError,
        match=r"TupleLiteralEnumEntity: the property 'choices\[1\]' of member 'ITEM' holds str "
        r"\(expected Literal\['a'\]\)",
    ):

        class TupleLiteralEnumEntity(BaseEnumEntity):
            """Declare a tuple of one permitted choice."""

            choices: tuple[Literal["a"], ...]

            ITEM = value(code="item", display_name="Item", choices=("a",))

            @field_validator("choices", mode="after")
            @classmethod
            def replace(cls, choices: tuple[Literal["a"], ...]) -> tuple[str, ...]:
                """Return a choice outside the permitted one."""
                return ("a", "b")


def test_none_is_refused_inside_a_tuple_for_a_non_nullable_union() -> None:
    """The null rule reaches a tuple item and the path names its index."""
    with pytest.raises(
        ValueError,
        match=r"TupleUnionEnumEntity: the property 'choices\[1\]' of member 'ITEM' holds NoneType "
        r"\(expected str \| int\)",
    ):

        class TupleUnionEnumEntity(BaseEnumEntity):
            """Declare a tuple of a union without null."""

            choices: tuple[str | int, ...]

            ITEM = value(code="item", display_name="Item", choices=("a",))

            @field_validator("choices", mode="after")
            @classmethod
            def replace(cls, choices: tuple[str | int, ...]) -> tuple[str | int | None, ...]:
                """Return null although the item annotation excludes it."""
                return ("a", None)


def test_none_is_accepted_inside_a_tuple_for_a_nullable_union() -> None:
    """A nullable item annotation accepts null in the same position."""

    class NullableTupleEnumEntity(BaseEnumEntity):
        """Declare a tuple whose items may be null."""

        choices: tuple[str | None, ...]

        ITEM = value(code="item", display_name="Item", choices=("a",))

        @field_validator("choices", mode="after")
        @classmethod
        def replace(cls, choices: tuple[str | None, ...]) -> tuple[str | None, ...]:
            """Return a null item the annotation permits."""
            return ("a", None)

    assert NullableTupleEnumEntity.ITEM.choices == ("a", None)


def test_a_literal_choice_is_matched_by_type_not_only_equality() -> None:
    """``True`` equals ``1`` but is not the literal ``1``, and the reverse holds too."""
    with pytest.raises(ValueError, match=r"property 'flag' of member 'ITEM' holds int \(expected Literal\[True\]\)"):

        class TrueLiteralEnumEntity(BaseEnumEntity):
            """Declare the literal true."""

            flag: Literal[True]

            ITEM = value(code="item", display_name="Item", flag=True)

            @field_validator("flag", mode="after")
            @classmethod
            def replace(cls, flag: bool) -> int:
                """Return an integer equal to true."""
                return 1

    with pytest.raises(ValueError, match=r"property 'count' of member 'ITEM' holds bool \(expected Literal\[1\]\)"):

        class OneLiteralEnumEntity(BaseEnumEntity):
            """Declare the literal one."""

            count: Literal[1]

            ITEM = value(code="item", display_name="Item", count=1)

            @field_validator("count", mode="after")
            @classmethod
            def replace(cls, count: int) -> bool:
                """Return a boolean equal to one."""
                return True


def test_bool_is_refused_for_an_int_property() -> None:
    """The leaf rule does not accept a boolean where the schema says integer."""
    with pytest.raises(
        ValueError, match=r"IntEnumEntity: the property 'count' of member 'ITEM' holds bool \(expected int\)"
    ):

        class IntEnumEntity(BaseEnumEntity):
            """Declare an integer property."""

            count: int

            ITEM = value(code="item", display_name="Item", count=1)

            @field_validator("count", mode="after")
            @classmethod
            def replace(cls, count: int) -> bool:
                """Return a boolean although the annotation excludes it."""
                return True


def test_true_is_accepted_for_the_boolean_literal() -> None:
    """The neighbour of the type distinction: the exact literal type is accepted."""

    class BoolLiteralEnumEntity(BaseEnumEntity):
        """Declare the literal true."""

        flag: Literal[True]

        ITEM = value(code="item", display_name="Item", flag=True)

        @field_validator("flag", mode="after")
        @classmethod
        def replace(cls, flag: bool) -> bool:
            """Return the same literal."""
            return True

    assert BoolLiteralEnumEntity.ITEM.flag is True


def test_a_property_annotated_only_none_is_refused_at_declaration() -> None:
    """Null alone is not a property type; it is supported only inside a union."""
    with pytest.raises(ValueError, match=r"ProbeEnumEntity: field 'note' is NoneType"):
        _build(**{"__annotations__": {"note": None}, "V": value(code="v", display_name="V", note=None)})


def test_an_int_result_is_refused_for_a_float_property() -> None:
    """A leaf compares the exact type: an integer is not a float, although JSON allows 1 as a number."""
    with pytest.raises(
        ValueError, match=r"FloatEnumEntity: the property 'ratio' of member 'ITEM' holds int \(expected float\)"
    ):

        class FloatEnumEntity(BaseEnumEntity):
            """Declare a float property."""

            ratio: float

            ITEM = value(code="item", display_name="Item", ratio=1.5)

            @field_validator("ratio", mode="after")
            @classmethod
            def replace(cls, ratio: float) -> int:
                """Return an integer although the annotation declares a float."""
                return 1


def test_a_float_result_publishes_for_a_float_property() -> None:
    """The neighbour of the exact-type refusal: the declared type is accepted."""

    class FloatEnumEntity(BaseEnumEntity):
        """Declare a float property."""

        ratio: float

        ITEM = value(code="item", display_name="Item", ratio=1.5)

        @field_validator("ratio", mode="after")
        @classmethod
        def replace(cls, ratio: float) -> float:
            """Return a float of the declared type."""
            return 2.5

    assert FloatEnumEntity.ITEM.ratio == 2.5
    assert type(FloatEnumEntity.ITEM.ratio) is float


def test_an_integer_input_is_coerced_before_the_completed_check() -> None:
    """The declaration path keeps Pydantic's coercion: a float property declared with 1 holds 1.0."""

    class FloatEnumEntity(BaseEnumEntity):
        """Declare a float property with an integer input."""

        ratio: float

        ITEM = value(code="item", display_name="Item", ratio=1)

    assert FloatEnumEntity.ITEM.ratio == 1.0
    assert type(FloatEnumEntity.ITEM.ratio) is float


def test_a_datetime_result_is_refused_for_a_date_property() -> None:
    """A datetime is a subclass of date, but the schema describes a date, not a date-time."""
    with pytest.raises(
        ValueError, match=r"DateEnumEntity: the property 'day' of member 'ITEM' holds datetime \(expected date\)"
    ):

        class DateEnumEntity(BaseEnumEntity):
            """Declare a date property."""

            day: date

            ITEM = value(code="item", display_name="Item", day=date(2020, 1, 2))

            @field_validator("day", mode="after")
            @classmethod
            def replace(cls, day: date) -> datetime:
                """Return a datetime although the annotation declares a date."""
                return datetime(2020, 1, 2, 3, 4)


def test_a_date_result_publishes_for_a_date_property() -> None:
    """The neighbour of the date refusal: the declared type is accepted."""

    class DateEnumEntity(BaseEnumEntity):
        """Declare a date property."""

        day: date

        ITEM = value(code="item", display_name="Item", day=date(2020, 1, 2))

        @field_validator("day", mode="after")
        @classmethod
        def replace(cls, day: date) -> date:
            """Return a date of the declared type."""
            return date(2021, 3, 4)

    assert DateEnumEntity.ITEM.day == date(2021, 3, 4)
    assert type(DateEnumEntity.ITEM.day) is date


def test_the_exact_leaf_type_holds_inside_a_tuple_and_a_nullable_union() -> None:
    """The leaf rule is reached through the container walk, and the path keeps the item index."""
    with pytest.raises(ValueError, match=r"property 'ratios\[1\]' of member 'ITEM' holds int \(expected float\)"):

        class TupleFloatEnumEntity(BaseEnumEntity):
            """Declare a tuple of floats."""

            ratios: tuple[float, ...]

            ITEM = value(code="item", display_name="Item", ratios=(1.5,))

            @field_validator("ratios", mode="after")
            @classmethod
            def replace(cls, ratios: tuple[float, ...]) -> tuple[float | int, ...]:
                """Return an integer in the second position."""
                return (1.5, 1)

    with pytest.raises(ValueError, match=r"property 'day' of member 'ITEM' holds datetime"):

        class NullableDateEnumEntity(BaseEnumEntity):
            """Declare a nullable date property."""

            day: date | None

            ITEM = value(code="item", display_name="Item", day=date(2020, 1, 2))

            @field_validator("day", mode="after")
            @classmethod
            def replace(cls, day: date | None) -> datetime:
                """Return a datetime in a nullable date position."""
                return datetime(2020, 1, 2, 3, 4)
