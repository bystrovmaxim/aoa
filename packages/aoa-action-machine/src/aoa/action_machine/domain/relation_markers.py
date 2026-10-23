# packages/aoa-action-machine/src/aoa/action_machine/domain/relation_markers.py
"""
**Relation markers** for entity fields: ``Inverse``, ``NoInverse``, ``NoGraphEdge`` and ``NoRelation``.

These types sit beside relation **container** types (``AssociationOne``, …) in
``typing.Annotated`` and in field defaults. They tell the gate **coordinator**
how edges connect, whether a back-reference exists, and supply human-readable
**scratch** for diagrams and generated docs.

A **specialization** — one head field pointing at one of N extension entities,
chosen by the value of a classifier field — is declared with the containers in
``specialization_containers.py``: ``Specialization[...]`` on the head,
``Generalization[...]`` on the extension, and the ``Classifier`` marker naming the
choosing field and the codes. Two forms of ``Inverse`` serve the pair: the head
names only its partner field, because the entities are already in the type; the
extension names both.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Disambiguate multi-edge graphs (e.g. two ``AssociationMany[OrderCoreEntity]`` fields
on ``CustomerCoreEntity``) with an explicit **inverse** pointer, require a **non-empty
relation description** on every declared edge, and support truly one-way links
via ``NoInverse``.

═══════════════════════════════════════════════════════════════════════════════
SCOPE (IN / OUT)
═══════════════════════════════════════════════════════════════════════════════

**In scope**
    Constructing immutable marker objects and validating their constructor inputs.
    Pairing with ``Annotated[..., Inverse(...)]`` or ``NoInverse()`` plus
    ``= Field(description=...)`` on entity model fields. Optional ``NoGraphEdge()``
    suppresses interchange edges for that field while keeping it in graph node metadata.
    ``NoRelation("reason")`` declares that a structural-entity field is an embedded value
    with no model relation at all, which the graph build refuses to guess.

**Out of scope**
    Proving the inverse field exists, types match, or ownership is compatible —
    **inspectors** and ``NodeGraphCoordinator.build()`` do that.
    Loading related rows from storage.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    Annotated[AssociationOne[CustomerCoreEntity], Inverse(CustomerCoreEntity, "orders")]
        │
        │  field metadata
        v
    = Field(description="…")
        │
        │  ``NodeGraphCoordinator.build()`` / ``EntityIntentResolver``
        v
    validated entity–entity edges (composition / aggregation / association)

Coordinator checks (conceptually): inverse field present and typed, every relation field
carries a description in ``FieldInfo.description``, ownership matrix, etc.

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
- **Runtime**: entity instances hold **container** values or an explicit ``None``;
  the description never reaches an instance.

"""

from __future__ import annotations

from typing import Any, cast


class Inverse:
    """
    AI-CORE-BEGIN
        ROLE: Explicit inverse relation pointer.
        CONTRACT: Bind current relation field to a concrete target entity field; on a
            specialization head the target entity is omitted, because the alternatives
            already name the entities.
        INVARIANTS: At least one of target entity and field name must be given; field
            name must be a non-empty string; target entity, when given, must be a type.
        AI-CORE-END
    """

    __slots__ = ("_field_name", "_target_entity")

    def __init__(self, target_entity: type | None = None, field_name: str | None = None) -> None:
        """
        Args:
            target_entity: Related entity class, or ``None`` on a specialization head.
            field_name: Name of the paired field on ``target_entity``.

        Raises:
            TypeError: ``target_entity`` is not a type, or ``field_name`` is not a ``str``.
            ValueError: Both arguments are absent, or ``field_name`` is empty or
                whitespace-only.
        """
        if target_entity is None and field_name is None:
            raise ValueError(
                "Inverse: at least one of target_entity and field_name must be given. "
                "Pass Inverse(TargetEntity, 'field') for a pair, or Inverse(field_name='field') "
                "on a specialization head, where the entities are already declared."
            )

        if target_entity is not None and not isinstance(target_entity, type):
            raise TypeError(
                f"Inverse: target_entity must be a type, " f"got {type(target_entity).__name__}: {target_entity!r}."
            )

        if field_name is None:
            raise TypeError("Inverse: field_name must be str, got NoneType: None.")

        if not isinstance(field_name, str):
            raise TypeError(f"Inverse: field_name must be str, " f"got {type(field_name).__name__}: {field_name!r}.")

        if not field_name.strip():
            raise ValueError("Inverse: field_name cannot be empty or whitespace-only.")

        object.__setattr__(self, "_target_entity", target_entity)
        object.__setattr__(self, "_field_name", field_name)

    @property
    def target_entity(self) -> type | None:
        """Related entity class, or ``None`` on a specialization head."""
        return cast(type | None, object.__getattribute__(self, "_target_entity"))

    @property
    def field_name(self) -> str:
        """Paired field name on ``target_entity``."""
        return cast(str, object.__getattribute__(self, "_field_name"))

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError("Inverse is frozen; assigning to attributes is not allowed.")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("Inverse is frozen; deleting attributes is not allowed.")

    def __repr__(self) -> str:
        target_entity = cast(type | None, object.__getattribute__(self, "_target_entity"))
        field_name = cast(str, object.__getattribute__(self, "_field_name"))
        if target_entity is None:
            return f"Inverse(field_name='{field_name}')"
        return f"Inverse({target_entity.__name__}, '{field_name}')"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Inverse):
            return NotImplemented
        target_entity = cast(type | None, object.__getattribute__(self, "_target_entity"))
        field_name = cast(str, object.__getattribute__(self, "_field_name"))
        return target_entity is other.target_entity and field_name == other.field_name

    def __hash__(self) -> int:
        target_entity = cast(type | None, object.__getattribute__(self, "_target_entity"))
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


class NoRelation:
    """
    AI-CORE-BEGIN
        ROLE: Explicit declaration that a structural-entity field embeds a value, not a relation.
        CONTRACT: Sit inside ``Annotated`` on a Core, Assoc, Detail or Spec field with a non-blank
            reason; the field stays an ordinary column and gains no relation edge, no foreign key
            and no storage inference.
        INVARIANTS: The reason is a non-empty string; the marker is frozen and value-equal; it is
            never combined with a relation container or another relation marker, and never marks a
            state entity, whose only form is a ``Lifecycle[...]`` field.
        AI-CORE-END
    """

    __slots__ = ("_reason",)

    def __init__(self, reason: str) -> None:
        """
        Args:
            reason: Why this field holds the entity as a value instead of as a relation.

        Raises:
            TypeError: ``reason`` is not a ``str``.
            ValueError: ``reason`` is empty or whitespace-only.
        """
        if not isinstance(reason, str):
            raise TypeError(f"NoRelation: reason must be str, got {type(reason).__name__}: {reason!r}.")
        if not reason.strip():
            raise ValueError("NoRelation: reason cannot be empty or whitespace-only.")
        object.__setattr__(self, "_reason", reason)

    @property
    def reason(self) -> str:
        """Return why the field holds an embedded value."""
        return cast(str, object.__getattribute__(self, "_reason"))

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError("NoRelation is frozen; assigning to attributes is not allowed.")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("NoRelation is frozen; deleting attributes is not allowed.")

    def __repr__(self) -> str:
        reason = cast(str, object.__getattribute__(self, "_reason"))
        return f"NoRelation({reason!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, NoRelation):
            return NotImplemented
        reason = cast(str, object.__getattribute__(self, "_reason"))
        return reason == other.reason

    def __hash__(self) -> int:
        reason = cast(str, object.__getattribute__(self, "_reason"))
        return hash(reason)
