# packages/aoa-action-machine/src/aoa/action_machine/graph/field_type_label.py
"""
field_type_label — a field's type as one clean name a diagram can show.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A diagram row has room for a short type, not for Python's internal spelling:
``str | None`` used to read ``UnionType[str, NoneType]`` and a relation
``AssociationOne[CurrencyEnumEntity]``. This module renders an annotation as a reader
would write it (spec 029, FR-030): an optional field ``str | None``, a relation by its
target (``X``, or ``X[]`` for many), a collection ``X[]``, literal values as values.
The full annotation is kept beside it (``field_annotation``) for the tooltip.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    annotation ──► Annotated? unwrap ──► Union? members, None last
               ├─► relation container ──► target (``[]`` for many)
               ├─► Generalization[X] ──► X · Specialization[A | B, K] ──► A | B
               ├─► list / set / frozenset / tuple[X, ...] ──► X[]
               ├─► Literal[...] ──► "a" | "b"
               └─► other generic ──► Name[args] · plain class ──► its name
"""

from __future__ import annotations

import types
from collections.abc import Callable
from typing import Annotated, Any, Literal, Union, get_args, get_origin

from aoa.action_machine.domain.relation_containers import BaseRelationMany, BaseRelationOne
from aoa.action_machine.domain.specialization_containers import Generalization, Specialization

_COLLECTIONS: tuple[Any, ...] = (list, set, frozenset)


def _name(annotation: Any) -> str:
    """A class by its qualified name, ``None`` as itself, anything else as Python prints it."""
    if annotation is type(None) or annotation is None:
        return "None"
    if isinstance(annotation, type):
        return annotation.__qualname__
    return getattr(annotation, "__qualname__", None) or str(annotation)


def _union(members: tuple[Any, ...]) -> str:
    """The members of a union joined by ``|``, ``None`` last."""
    present = [field_type_label(member) for member in members if member is not type(None)]
    if len(present) != len(members):
        present.append("None")
    return " | ".join(present)


def _subclass_of(origin: Any, base: type) -> bool:
    """Whether a generic's origin is a class derived from ``base``."""
    return isinstance(origin, type) and issubclass(origin, base)


def _many(args: tuple[Any, ...]) -> str:
    """What a collection or a many-relation holds, as ``X[]``."""
    return f"{field_type_label(args[0])}[]"


def _first(args: tuple[Any, ...]) -> str:
    """What a one-relation, a generalization or a specialization points at."""
    return field_type_label(args[0])


#: Containers shown by what they hold: (does this origin with these arguments match?, how to show it).
_CONTAINERS: tuple[tuple[Callable[[Any, tuple[Any, ...]], bool], Callable[[tuple[Any, ...]], str]], ...] = (
    (lambda origin, args: _subclass_of(origin, BaseRelationOne) and len(args) == 1, _first),
    (lambda origin, args: _subclass_of(origin, BaseRelationMany) and len(args) == 1, _many),
    (lambda origin, args: origin in (Generalization, Specialization) and len(args) >= 1, _first),
    (lambda origin, args: origin in _COLLECTIONS and len(args) == 1, _many),
    (lambda origin, args: origin is tuple and len(args) == 2 and args[1] is Ellipsis, _many),
)


def _literal(args: tuple[Any, ...]) -> str:
    """Literal values as values: strings quoted, the rest as Python prints them."""
    return " | ".join(f'"{value}"' if isinstance(value, str) else repr(value) for value in args)


#: Forms shown by their arguments alone.
_FORMS: dict[Any, Callable[[tuple[Any, ...]], str]] = {
    Annotated: _first,
    Union: _union,
    types.UnionType: _union,
    Literal: _literal,
}


def _origin_and_args(annotation: Any) -> tuple[Any, tuple[Any, ...]]:
    """``typing``'s origin and arguments, or a parametrised pydantic model's own (``get_origin`` sees none there)."""
    metadata = getattr(annotation, "__pydantic_generic_metadata__", None)
    if isinstance(metadata, dict) and metadata.get("origin") is not None:
        return metadata["origin"], tuple(metadata.get("args") or ())
    return get_origin(annotation), get_args(annotation)


def field_type_label(annotation: Any) -> str:
    """
    One clean name for ``annotation``, as a diagram row shows it (spec 029, FR-030).

    AI-CORE-BEGIN
    ROLE: Render a field annotation as a reader writes it, for ``EntityField`` vertices' ``field_type``.
    CONTRACT: ``X | None`` and ``Optional[X]`` → ``X | None``; a one-relation, ``Generalization[X]`` → ``X``; a many-relation, ``list[X]``, ``set[X]``, ``tuple[X, ...]`` → ``X[]``; ``Specialization[A | B, K]`` → ``A | B``; ``Literal["a", "b"]`` → ``"a" | "b"``; other generics ``Name[args]``.
    INVARIANTS: Pure and total; ``Annotated`` metadata never shows; ``None`` is always last in a union.
    AI-CORE-END
    """
    origin, args = _origin_and_args(annotation)
    form = _FORMS.get(origin)
    if form is not None:
        return form(args)
    if origin is None:
        return _name(annotation)
    for matches, show in _CONTAINERS:
        if matches(origin, args):
            return show(args)
    rendered = ", ".join("..." if arg is Ellipsis else field_type_label(arg) for arg in args)
    return f"{_name(origin)}[{rendered}]" if rendered else _name(origin)
