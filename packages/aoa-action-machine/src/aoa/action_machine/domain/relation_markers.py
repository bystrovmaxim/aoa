# packages/aoa-action-machine/src/aoa/action_machine/domain/relation_markers.py
"""
**Relation markers** for entity fields: ``Inverse``, ``NoInverse``, ``NoGraphEdge``, ``Rel``,
``Specialization``, ``Generalization``, and ``By``.

These types sit beside relation **container** types (``AssociationOne``, …) in
``typing.Annotated`` and in field defaults. They tell the gate **coordinator**
how edges connect, whether a back-reference exists, and supply human-readable
**scratch** for diagrams and generated docs.

``Specialization``, ``Generalization`` and ``By`` declare a **specialization**:
one head field that points at one of N extension entities, chosen by the value of
a classifier field. A container cannot express it — a container argument holds one
target type — so the alternatives live in these markers and the type position
carries the value type alone. Two forms of ``Inverse`` serve the pair: the head
names only its partner field, because the entities are already in the markers;
the extension names both.

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
            raise TypeError(f"Rel: description must be str, " f"got {type(description).__name__}: {description!r}.")

        if not description.strip():
            raise ValueError(
                "Rel: description cannot be empty or whitespace-only. " "Provide a non-empty relation description."
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


class Specialization:
    """
    AI-CORE-BEGIN
        ROLE: One alternative target of a specialization field, with the code that selects it.
        CONTRACT: Declare ``target_entity`` and the ``classifier`` code that chooses it; read on the
            head, paired with a ``Generalization`` on the alternative itself.
        INVARIANTS: target entity must be a type; classifier must be a non-empty string.
        AI-CORE-END
    """

    __slots__ = ("_classifier", "_target_entity")

    def __init__(self, target_entity: type, classifier: str) -> None:
        """
        Args:
            target_entity: The extension entity class this alternative denotes.
            classifier: The variant code whose value selects this alternative.

        Raises:
            TypeError: ``target_entity`` is not a type, or ``classifier`` is not a ``str``.
            ValueError: ``classifier`` is empty or whitespace-only.
        """
        if not isinstance(target_entity, type):
            raise TypeError(
                f"Specialization: target_entity must be a type, "
                f"got {type(target_entity).__name__}: {target_entity!r}."
            )

        if not isinstance(classifier, str):
            raise TypeError(
                f"Specialization: classifier must be str, " f"got {type(classifier).__name__}: {classifier!r}."
            )

        if not classifier.strip():
            raise ValueError("Specialization: classifier cannot be empty or whitespace-only.")

        object.__setattr__(self, "_target_entity", target_entity)
        object.__setattr__(self, "_classifier", classifier)

    @property
    def target_entity(self) -> type:
        """The extension entity class this alternative denotes."""
        return cast(type, object.__getattribute__(self, "_target_entity"))

    @property
    def classifier(self) -> str:
        """The variant code whose value selects this alternative."""
        return cast(str, object.__getattribute__(self, "_classifier"))

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError("Specialization is frozen; assigning to attributes is not allowed.")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("Specialization is frozen; deleting attributes is not allowed.")

    def __repr__(self) -> str:
        target_entity = cast(type, object.__getattribute__(self, "_target_entity"))
        classifier = cast(str, object.__getattribute__(self, "_classifier"))
        return f"Specialization({target_entity.__name__}, classifier='{classifier}')"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Specialization):
            return NotImplemented
        target_entity = cast(type, object.__getattribute__(self, "_target_entity"))
        classifier = cast(str, object.__getattribute__(self, "_classifier"))
        return target_entity is other.target_entity and classifier == other.classifier

    def __hash__(self) -> int:
        target_entity = cast(type, object.__getattribute__(self, "_target_entity"))
        classifier = cast(str, object.__getattribute__(self, "_classifier"))
        return hash((id(target_entity), classifier))


class Generalization:
    """
    AI-CORE-BEGIN
        ROLE: The reverse declaration on an extension: the head it belongs to, with its own code.
        CONTRACT: Declare ``head_entity`` and the same ``classifier`` code the head declares beside
            this class; the build compares the two.
        INVARIANTS: head entity must be a type; classifier must be a non-empty string.
        AI-CORE-END
    """

    __slots__ = ("_classifier", "_head_entity")

    def __init__(self, head_entity: type, classifier: str) -> None:
        """
        Args:
            head_entity: The head entity class this extension belongs to.
            classifier: The variant code, declared independently and compared with the head's.

        Raises:
            TypeError: ``head_entity`` is not a type, or ``classifier`` is not a ``str``.
            ValueError: ``classifier`` is empty or whitespace-only.
        """
        if not isinstance(head_entity, type):
            raise TypeError(
                f"Generalization: head_entity must be a type, " f"got {type(head_entity).__name__}: {head_entity!r}."
            )

        if not isinstance(classifier, str):
            raise TypeError(
                f"Generalization: classifier must be str, " f"got {type(classifier).__name__}: {classifier!r}."
            )

        if not classifier.strip():
            raise ValueError("Generalization: classifier cannot be empty or whitespace-only.")

        object.__setattr__(self, "_head_entity", head_entity)
        object.__setattr__(self, "_classifier", classifier)

    @property
    def head_entity(self) -> type:
        """The head entity class this extension belongs to."""
        return cast(type, object.__getattribute__(self, "_head_entity"))

    @property
    def classifier(self) -> str:
        """The variant code, compared with the one the head declares."""
        return cast(str, object.__getattribute__(self, "_classifier"))

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError("Generalization is frozen; assigning to attributes is not allowed.")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("Generalization is frozen; deleting attributes is not allowed.")

    def __repr__(self) -> str:
        head_entity = cast(type, object.__getattribute__(self, "_head_entity"))
        classifier = cast(str, object.__getattribute__(self, "_classifier"))
        return f"Generalization({head_entity.__name__}, classifier='{classifier}')"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Generalization):
            return NotImplemented
        head_entity = cast(type, object.__getattribute__(self, "_head_entity"))
        classifier = cast(str, object.__getattribute__(self, "_classifier"))
        return head_entity is other.head_entity and classifier == other.classifier

    def __hash__(self) -> int:
        head_entity = cast(type, object.__getattribute__(self, "_head_entity"))
        classifier = cast(str, object.__getattribute__(self, "_classifier"))
        return hash((id(head_entity), classifier))


class By:
    """
    AI-CORE-BEGIN
        ROLE: Names the classifier field whose value selects a specialization alternative.
        CONTRACT: Sit in the head field's ``Annotated`` metadata beside the ``Specialization``
            markers; the field it names must be a scalar field of the same entity.
        INVARIANTS: field name must be a non-empty string; the marker is an object, not a keyword,
            because a bare keyword does not parse inside ``Annotated``.
        AI-CORE-END
    """

    __slots__ = ("_field_name",)

    def __init__(self, field_name: str) -> None:
        """
        Args:
            field_name: Name of the classifier field on the same entity.

        Raises:
            TypeError: ``field_name`` is not a ``str``.
            ValueError: ``field_name`` is empty or whitespace-only.
        """
        if not isinstance(field_name, str):
            raise TypeError(f"By: field_name must be str, " f"got {type(field_name).__name__}: {field_name!r}.")

        if not field_name.strip():
            raise ValueError("By: field_name cannot be empty or whitespace-only.")

        object.__setattr__(self, "_field_name", field_name)

    @property
    def field_name(self) -> str:
        """Name of the classifier field on the same entity."""
        return cast(str, object.__getattribute__(self, "_field_name"))

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError("By is frozen; assigning to attributes is not allowed.")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("By is frozen; deleting attributes is not allowed.")

    def __repr__(self) -> str:
        field_name = cast(str, object.__getattribute__(self, "_field_name"))
        return f"By('{field_name}')"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, By):
            return NotImplemented
        field_name = cast(str, object.__getattribute__(self, "_field_name"))
        return field_name == other.field_name

    def __hash__(self) -> int:
        field_name = cast(str, object.__getattribute__(self, "_field_name"))
        return hash(field_name)
