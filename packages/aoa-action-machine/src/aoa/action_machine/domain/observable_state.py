# packages/aoa-action-machine/src/aoa/action_machine/domain/observable_state.py
"""
Observable state — what rule 2 of #399 compares between a value and its read-back copy.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A Result read back from its own JSON must hold the same values; for every entity,
the same loaded fields; for every relation, the same ids, the same loaded state and
the same loaded entities in the same order; for a declared value (a status or a
dictionary value), the same declared object. Equality does not compare that: a Many
relation loaded with zero rows equals one never loaded. ``observable_difference``
does, and returns the first difference with its path, such as
``$.order.lines.entities[0].quantity: 2 != 3``, or ``None``. The read-back tests use
it, and so will the cache write. Equality of every type stays as it is.

═══════════════════════════════════════════════════════════════════════════════
RULES, IN ORDER
═══════════════════════════════════════════════════════════════════════════════

1. Different types differ (a UUID and its string, an int and a float).
2. A declared value (an enumeration or state value) is the same declared object.
3. A lifecycle has the same declared current status.
4. A One relation has the same id and loaded state, then the same entity when loaded;
   a Many relation the same ids and loaded state, then the same entities in order.
5. A model holds the same fields, in declaration order, each the same.
6. A list or tuple has the same length, item by item; a mapping the same keys in
   order, value by value.
7. Anything else is equal by ``==``.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from pydantic import BaseModel

from aoa.action_machine.domain.enum_entity import BaseEnumEntity
from aoa.action_machine.domain.lifecycle import Lifecycle
from aoa.action_machine.domain.relation_containers import BaseRelationMany, BaseRelationOne
from aoa.action_machine.domain.state_entity import BaseStateEntity

__all__ = ["observable_difference"]


def _held_fields(model: BaseModel) -> list[str]:
    """The declared fields ``model`` holds, in declaration order (a partial entity holds fewer)."""
    held = object.__getattribute__(model, "__dict__")
    return [name for name in type(model).model_fields if name in held]


def _items_difference(before: Any, after: Any, path: str) -> str | None:
    if len(before) != len(after):
        return f"{path}: length {len(before)} != {len(after)}"
    for index, (item_before, item_after) in enumerate(zip(before, after, strict=True)):
        found = observable_difference(item_before, item_after, f"{path}[{index}]")
        if found:
            return found
    return None


def _model_difference(before: BaseModel, after: BaseModel, path: str) -> str | None:
    fields_before, fields_after = _held_fields(before), _held_fields(after)
    if fields_before != fields_after:
        return f"{path}: loaded fields {fields_before} != {fields_after}"
    held_before = object.__getattribute__(before, "__dict__")
    held_after = object.__getattribute__(after, "__dict__")
    for name in fields_before:
        found = observable_difference(held_before[name], held_after[name], f"{path}.{name}")
        if found:
            return found
    return None


def _relation_difference(before: Any, after: Any, path: str) -> str | None:
    if isinstance(before, BaseRelationOne):
        if type(before.id) is not type(after.id) or before.id != after.id:
            return f"{path}: id {before.id!r} != {after.id!r}"
        if before.is_loaded != after.is_loaded:
            return f"{path}: loaded {before.is_loaded} != {after.is_loaded}"
        return observable_difference(before.entity, after.entity, f"{path}.entity") if before.is_loaded else None
    found = _items_difference(before.ids, after.ids, f"{path}.ids")
    if found:
        return f"{path}: ids {before.ids!r} != {after.ids!r}"
    if before.is_loaded != after.is_loaded:
        return f"{path}: loaded {before.is_loaded} != {after.is_loaded}"
    return _items_difference(before.entities, after.entities, f"{path}.entities") if before.is_loaded else None


def _declared_difference(before: Any, after: Any, path: str) -> str | None:
    if before is after:
        return None
    return f"{path}: not the declared {type(before).__name__} {getattr(before, 'code', before)!r}"


def _lifecycle_difference(before: Lifecycle[Any], after: Lifecycle[Any], path: str) -> str | None:
    if before.current_status is after.current_status:
        return None
    return f"{path}: status {before.current_state!r} != {after.current_state!r}"


def _mapping_difference(before: Mapping[Any, Any], after: Mapping[Any, Any], path: str) -> str | None:
    if list(before) != list(after):
        return f"{path}: keys {list(before)} != {list(after)}"
    for key in before:
        found = observable_difference(before[key], after[key], f"{path}[{key!r}]")
        if found:
            return found
    return None


# Checked in this order; the first kind that matches decides. Anything else is compared by ==.
_RULES: tuple[tuple[tuple[type, ...], Callable[[Any, Any, str], str | None]], ...] = (
    ((BaseEnumEntity, BaseStateEntity), _declared_difference),
    ((Lifecycle,), _lifecycle_difference),
    ((BaseRelationOne, BaseRelationMany), _relation_difference),
    ((BaseModel,), _model_difference),
    ((list, tuple), _items_difference),
    ((Mapping,), _mapping_difference),
)


def observable_difference(before: Any, after: Any, path: str = "$") -> str | None:
    """
    Return the first place ``before`` and ``after`` differ in observable state, or ``None``.

    Args:
        before: the value as it was, such as a Result before it is written.
        after: the value to compare, such as the same Result read back from its JSON.
        path: where the two values sit, used to build the path of a difference.

    Returns:
        ``"<path>: <what differs>"`` for the first difference found, or ``None`` when the two are the same.
    """
    if type(before) is not type(after):
        return f"{path}: {type(before).__name__} != {type(after).__name__}"
    for kinds, compare in _RULES:
        if isinstance(before, kinds):
            return compare(before, after, path)
    return None if before == after else f"{path}: {before!r} != {after!r}"
