# packages/aoa-action-machine/src/aoa/action_machine/domain/specialization_containers.py
"""
Specialization **containers** and their markers: a field that points at one of N targets.

A relation field's target type is one type, whichever ownership container is chosen.
When the continuation of a row lives in one of several tables, and the table is chosen
by the value of a classifier field, one type is not enough to say it:

``Specialization[CreatedEvent | UpdatedEvent | DeletedEvent]``
    the head's side — a reference to one of the declared alternatives, carrying which
    one it is. Subscripting it with a union states the whole declaration in the type
    position, the way ``AssociationOne[CustomerEntity]`` states a single target.

``Generalization[EventEntity]``
    the extension's side — a reference back to its head.

Both are **pydantic models**, so subscripting one produces a real class: a field of that
type accepts an instance of it, exactly as the ownership containers behave. The metadata
that cannot be expressed as a type — which field chooses, which codes exist, which field
is paired — travels in the ``Classifier`` and ``Inverse`` markers beside it.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Let one head field name several alternative targets and the codes that select them, so
that the model states which table a row continues in, the graph can publish the
code-to-table mapping, and a resource can resolve a row's code explicitly.

═══════════════════════════════════════════════════════════════════════════════
SCOPE (IN / OUT)
═══════════════════════════════════════════════════════════════════════════════

**In scope**
    Holding the identifier of the related row, the variant a head-side link is, and the
    hydrated row when one was loaded.
    Immutability after construction.
    Declaring the classifier field, and the codes as a ``Literal`` beside the field.

**Out of scope**
    Deciding whether a code in the data is one the model declares and matching it to a
    class — that is the resource's own explicit step, and the declared mapping it reads
    is published by the graph.
    Loading rows from storage.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    head row:  media = "first",  pressing = ?

        the resource reads `media` and resolves it against the declared mapping
            │
            ├─ code not declared             -> an explicit failure, never "no relation"
            │
            └─ code declared
                 ├─ row loaded    -> Specialization[...](id=…, variant=…, entity=FirstPressEntity(...))
                 └─ row not loaded-> Specialization[...](id=…, variant=…)   # id and variant only

    the extension's side mirrors it: Generalization[Head](id=…, entity=<head row>)

═══════════════════════════════════════════════════════════════════════════════
RATIONALE
═══════════════════════════════════════════════════════════════════════════════

The alternatives live in the **type argument** rather than in a marker because the type
argument is the one place pydantic validates: a narrower subscription refuses the other
alternatives, and a class the union does not list is refused on assignment. A marker
carries only what a type cannot say — the choosing field, the codes, the paired field.

Neither container inherits the ownership containers: specialization is classification,
not ownership, and an ``isinstance`` check against composition, aggregation or
association keeps meaning exactly what it meant.

``entity`` is excluded from ``repr``: a head row and its extension can reference each
other, and printing one would otherwise print the other forever.

═══════════════════════════════════════════════════════════════════════════════
LIFECYCLE (IMPORT VS BUILD VS RUNTIME)
═══════════════════════════════════════════════════════════════════════════════

- **Import**: the containers and markers are defined.
- **Build**: the parser reads the union from the container's type argument and the
  markers from the field's metadata; the rules are checked across the whole model.
- **Runtime**: a resource resolves a code and constructs the container it declares.

"""

from __future__ import annotations

from typing import Any, Literal, cast, get_args, get_origin

from pydantic import BaseModel, ConfigDict, Field


class Specialization[T](BaseModel):
    """
    AI-CORE-BEGIN
        ROLE: Head-side container: a link to one of the declared alternatives.
        CONTRACT: ``id`` and ``variant`` are always present; ``entity`` holds the hydrated row
            when one was loaded. Subscript with the union of the alternatives.
        INVARIANTS: A value assigned to ``entity`` must be one of the classes in the type
            argument; the container is frozen after construction.
        AI-CORE-END
    """

    model_config = ConfigDict(frozen=True)

    id: Any = Field(description="Identifier of the related extension row")
    variant: str = Field(description="The declared code that selects this alternative")
    entity: T | None = Field(default=None, repr=False, description="The hydrated extension row")


class Generalization[T](BaseModel):
    """
    AI-CORE-BEGIN
        ROLE: Extension-side container: a link back to the head this row belongs to.
        CONTRACT: ``id`` is always present; ``entity`` holds the hydrated head row when loaded.
            Subscript with the head class.
        INVARIANTS: A value assigned to ``entity`` must be the class in the type argument;
            the container is frozen after construction.
        AI-CORE-END
    """

    model_config = ConfigDict(frozen=True)

    id: Any = Field(description="Identifier of the related head row")
    entity: T | None = Field(default=None, repr=False, description="The hydrated head row")


class Classifier:
    """
    AI-CORE-BEGIN
        ROLE: Marks a specialization field on the head: which field chooses, and which codes exist.
        CONTRACT: ``field`` names the classifier field on the same entity; ``codes`` is a
            ``Literal`` of the declared codes, in the order the alternatives are written.
        INVARIANTS: ``field`` is a non-empty string; ``codes`` is a ``Literal`` with at least
            one member; every member is a non-empty string; frozen.
        AI-CORE-END
    """

    __slots__ = ("_codes", "_field")

    def __init__(self, field: str, codes: Any) -> None:
        """
        Args:
            field: Name of the classifier field whose value selects the alternative.
            codes: A ``Literal`` of the declared codes, in declaration order.

        Raises:
            TypeError: ``field`` is not a ``str``, or ``codes`` is not a ``Literal``.
            ValueError: ``field`` is empty or whitespace-only, the ``Literal`` has no members,
                or a member is empty or not a string.
        """
        if not isinstance(field, str):
            raise TypeError(f"Classifier: field must be str, got {type(field).__name__}: {field!r}.")

        if not field.strip():
            raise ValueError("Classifier: field cannot be empty or whitespace-only.")

        if get_origin(codes) is not Literal:
            raise TypeError(
                f"Classifier: codes must be a Literal of codes, "
                f"got {type(codes).__name__}: {codes!r}."
            )

        members = get_args(codes)
        if not members:
            raise ValueError("Classifier: codes must declare at least one code.")

        for code in members:
            if not isinstance(code, str):
                raise TypeError(f"Classifier: codes must be str, got {type(code).__name__}: {code!r}.")
            if not code.strip():
                raise ValueError("Classifier: codes cannot contain an empty or whitespace-only code.")

        object.__setattr__(self, "_field", field)
        object.__setattr__(self, "_codes", codes)

    @property
    def field(self) -> str:
        """Name of the classifier field whose value selects the alternative."""
        return cast(str, object.__getattribute__(self, "_field"))

    @property
    def codes(self) -> Any:
        """The ``Literal`` of declared codes, in declaration order."""
        return object.__getattribute__(self, "_codes")

    @property
    def code_values(self) -> tuple[str, ...]:
        """The declared codes as plain strings, in declaration order."""
        return cast(tuple[str, ...], get_args(object.__getattribute__(self, "_codes")))

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError("Classifier is frozen; assigning to attributes is not allowed.")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("Classifier is frozen; deleting attributes is not allowed.")

    def __repr__(self) -> str:
        field = cast(str, object.__getattribute__(self, "_field"))
        codes = object.__getattribute__(self, "_codes")
        return f"Classifier(field={field!r}, codes={codes!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Classifier):
            return NotImplemented
        return self.field == other.field and self.codes == other.codes

    def __hash__(self) -> int:
        return hash((self.field, str(self.codes)))
