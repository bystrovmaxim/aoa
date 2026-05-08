# packages/aoa-action-machine/src/aoa/action_machine/domain/relation_markers.py
"""
**Relation markers** for entity fields: ``Inverse``, ``NoInverse``, ``NoGraphEdge``, and ``Rel``.

These types sit beside relation **container** types (``AssociationOne``, …) in
``typing.Annotated`` and in field defaults. They tell the gate **coordinator**
how edges connect, whether a back-reference exists, and supply human-readable
**scratch** for diagrams and generated docs.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Disambiguate multi-edge graphs (e.g. two ``AssociationMany[OrderEntity]`` fields
on ``CustomerEntity``) with an explicit **inverse** pointer, require a **non-empty
relation description** on every declared edge, and support truly one-way links
via ``NoInverse``.

═══════════════════════════════════════════════════════════════════════════════
SCOPE (IN / OUT)
═══════════════════════════════════════════════════════════════════════════════

**In scope**
    Constructing immutable marker objects and validating their constructor inputs.
    Pairing with ``Annotated[..., Inverse(...)]`` or ``NoInverse()`` plus
    ``= Rel(description=...)`` on entity model fields. Optional ``NoGraphEdge()``
    suppresses interchange edges for that field while keeping it in graph node metadata.

**Out of scope**
    Proving the inverse field exists, types match, or ownership is compatible —
    **inspectors** and ``NodeGraphCoordinator.build()`` do that.
    Loading related rows from storage.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    Annotated[AssociationOne[CustomerEntity], Inverse(CustomerEntity, "orders")]
        │
        │  class default
        v
    = Rel(description="…")
        │
        │  ``NodeGraphCoordinator.build()`` / ``EntityIntentResolver``
        v
    validated entity–entity edges (composition / aggregation / association)

Coordinator checks (conceptually): inverse field present and typed, both ends
carry ``Rel``, ownership matrix, etc.

═══════════════════════════════════════════════════════════════════════════════
RATIONALE
═══════════════════════════════════════════════════════════════════════════════

Heuristic inverse discovery breaks when multiple fields share the same target
type; an explicit ``Inverse(Target, "field")`` is one line, refactor-friendly,
and matches how architects draw navigable graphs. Mandatory descriptions keep
the model a **specification**, not just code. ``NoInverse`` makes one-way edges
explicit instead of relying on absence, which would be ambiguous for the
coordinator.

═══════════════════════════════════════════════════════════════════════════════
LIFECYCLE (IMPORT VS BUILD VS RUNTIME)
═══════════════════════════════════════════════════════════════════════════════

- **Import**: markers are instantiated in class bodies as annotations/defaults.
- **Build**: coordinator consumes markers from entity metadata.
- **Runtime**: entity instances hold **container** values; ``Rel`` typically
  remains only as the class-level default unless the constructor still sees it
  (e.g. optional relation omitted in ``build()``).

"""

from __future__ import annotations

from typing import Any, cast


class Inverse:
    """
AI-CORE-BEGIN
    ROLE: Explicit inverse relation pointer.
    CONTRACT: Bind current relation field to a concrete target entity field.
    INVARIANTS: target entity must be a type; field name must be non-empty string.
    AI-CORE-END
"""

    __slots__ = ("_field_name", "_target_entity")

    def __init__(self, target_entity: type, field_name: str) -> None:
        """
        Args:
            target_entity: Related entity class.
            field_name: Name of the paired field on ``target_entity``.

        Raises:
            TypeError: ``target_entity`` is not a type, or ``field_name`` is not
                a ``str``.
            ValueError: ``field_name`` is empty or whitespace-only.
        """
        if not isinstance(target_entity, type):
            raise TypeError(
                f"Inverse: target_entity must be a type, "
                f"got {type(target_entity).__name__}: {target_entity!r}."
            )

        if not isinstance(field_name, str):
            raise TypeError(
                f"Inverse: field_name must be str, "
                f"got {type(field_name).__name__}: {field_name!r}."
            )

        if not field_name.strip():
            raise ValueError(
                "Inverse: field_name cannot be empty or whitespace-only."
            )

        object.__setattr__(self, "_target_entity", target_entity)
        object.__setattr__(self, "_field_name", field_name)

    @property
    def target_entity(self) -> type:
        """Related entity class."""
        return cast(type, object.__getattribute__(self, "_target_entity"))

    @property
    def field_name(self) -> str:
        """Paired field name on ``target_entity``."""
        return cast(str, object.__getattribute__(self, "_field_name"))

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError("Inverse is frozen; assigning to attributes is not allowed.")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("Inverse is frozen; deleting attributes is not allowed.")

    def __repr__(self) -> str:
        target_entity = cast(type, object.__getattribute__(self, "_target_entity"))
        field_name = cast(str, object.__getattribute__(self, "_field_name"))
        return f"Inverse({target_entity.__name__}, '{field_name}')"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Inverse):
            return NotImplemented
        target_entity = cast(type, object.__getattribute__(self, "_target_entity"))
        field_name = cast(str, object.__getattribute__(self, "_field_name"))
        return (
            target_entity is other.target_entity
            and field_name == other.field_name
        )

    def __hash__(self) -> int:
        target_entity = cast(type, object.__getattribute__(self, "_target_entity"))
        field_name = cast(str, object.__getattribute__(self, "_field_name"))
        return hash((id(target_entity), field_name))


class NoInverse:
    """
AI-CORE-BEGIN
    ROLE: Explicit marker for one-way relation edges.
    CONTRACT: Signals intentional absence of reverse field mapping.
    INVARIANTS: Stateless frozen marker object.
    AI-CORE-END
"""

    __slots__ = ()

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError("NoInverse is frozen; assigning to attributes is not allowed.")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("NoInverse is frozen; deleting attributes is not allowed.")

    def __repr__(self) -> str:
        return "NoInverse()"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, NoInverse):
            return NotImplemented
        return True

    def __hash__(self) -> int:
        return hash("NoInverse")


class NoGraphEdge:
    """
AI-CORE-BEGIN
    ROLE: Explicit opt-out of graph materialization for one relation field.
    CONTRACT: Stateless frozen marker; combinable with ``Inverse`` or ``NoInverse``.
    INVARIANTS: No attributes; singleton semantics via ``__eq__`` / ``__hash__``.
    AI-CORE-END
"""

    __slots__ = ()

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError("NoGraphEdge is frozen; assigning to attributes is not allowed.")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("NoGraphEdge is frozen; deleting attributes is not allowed.")

    def __repr__(self) -> str:
        return "NoGraphEdge()"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, NoGraphEdge):
            return NotImplemented
        return True

    def __hash__(self) -> int:
        return hash("NoGraphEdge")


class Rel:
    """
AI-CORE-BEGIN
    ROLE: Mandatory relation description carrier.
    CONTRACT: Provide non-empty documentation text for one direction of an entity relation edge.
    INVARIANTS: Description is validated and immutable after construction.
    AI-CORE-END
"""

    __slots__ = ("_description",)

    def __init__(self, *, description: str) -> None:
        """
        Args:
            description: Non-empty relation description (keyword-only).

        Raises:
            TypeError: ``description`` is not a ``str``.
            ValueError: Empty or whitespace-only ``description``.
        """
        if not isinstance(description, str):
            raise TypeError(
                f"Rel: description must be str, "
                f"got {type(description).__name__}: {description!r}."
            )

        if not description.strip():
            raise ValueError(
                "Rel: description cannot be empty or whitespace-only. "
                "Provide a non-empty relation description."
            )

        object.__setattr__(self, "_description", description)

    @property
    def description(self) -> str:
        """Relation description for this direction."""
        return cast(str, object.__getattribute__(self, "_description"))

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError("Rel is frozen; assigning to attributes is not allowed.")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("Rel is frozen; deleting attributes is not allowed.")

    def __repr__(self) -> str:
        description = cast(str, object.__getattribute__(self, "_description"))
        return f"Rel(description='{description}')"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Rel):
            return NotImplemented
        description = cast(str, object.__getattribute__(self, "_description"))
        return description == other.description

    def __hash__(self) -> int:
        description = cast(str, object.__getattribute__(self, "_description"))
        return hash(description)
