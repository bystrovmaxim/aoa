# packages/aoa-action-machine/src/aoa/action_machine/resources/entities/walk.py
"""
walk_answer — walk a resource's answer against its ``EntitiesPlan``.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A resource **is** a database: it may return only the entities its ``@entities``
lists. When a public method returns, the wrapper hands the answer to
:func:`walk_answer`, which compares every loaded entity with the plan:

1. **Exact class** — ``type(value)`` must be a listed class. A subclass of a listed
   class is not listed and is refused; a partial answer of a listed class is that
   same class and passes.
2. **The root and the containers** — a list, a tuple and the values of a mapping are
   walked, so every element is checked. The path names attributes as
   ``order.lines[0].product``, with ``[index]`` for a sequence and ``[key]`` for a
   mapping.
3. **Relations** — a relation that leads out of the list passes only **unloaded**:
   its container holds the id and no entity. A loaded entity of an unlisted class is
   refused even when it is a partial one that holds only its id.
4. **The model's own** — a dictionary member (``BaseEnumEntity``) and a lifecycle
   state (``BaseStateEntity``) belong to the model, not to a database, and pass
   wherever they appear.
5. **A resource without ``@entities``** — every entity is refused, saying the
   declaration is missing.

The first look at an answer is one ``isinstance(value, BaseEntity)`` check, so an
answer that carries no entity passes without walking anything. A listed class from
which no relation reaches outside the list is checked by type only — the plan marks
those classes, and the walk does not read their fields.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    answer ──isinstance(BaseEntity)?── yes ──► dictionary member / lifecycle state → pass
      │                                          │ otherwise
      no                                         ▼
      │                                  exact class listed? ── no ──► ResourceEntitiesError
      ▼                                          │ yes
    list / tuple / mapping / relation            ▼
      │  (walk each element)              plan.needs_walk(class)? ── no ──► pass
      │                                          │ yes
      └──────────────► walk each field value ────┘

"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from aoa.action_machine.domain.entity import BaseEntity
from aoa.action_machine.domain.enum_entity import BaseEnumEntity
from aoa.action_machine.domain.relation_containers import BaseRelationMany, BaseRelationOne
from aoa.action_machine.domain.state_entity import BaseStateEntity
from aoa.action_machine.exceptions.resource_entities_error import ResourceEntitiesError
from aoa.action_machine.resources.entities.plan import EntitiesPlan

__all__ = ["walk_answer"]

_ANSWER_ROOT = "answer"
"""The path of a root answer when the caller names none."""


def walk_answer(
    value: Any,
    plan: EntitiesPlan,
    resource_name: str,
    entry_point: str,
    path: str = "",
) -> None:
    """
    Walk one answer and refuse the first entity the resource does not list.

    Args:
        value: The answer a public method returned, a value yielded by its async
            generator, or any value nested inside either.
        plan: The frozen plan of the resource that answered.
        resource_name: The resource class name the refusal names.
        entry_point: The public method name the refusal names.
        path: The path of ``value`` inside the answer. Empty at the root; the root is
            then named ``answer``.

    Raises:
        ResourceEntitiesError: A loaded entity's exact class is not listed, or the
            resource declares no ``@entities``.
    """
    _walk(value, plan, resource_name, entry_point, path or _ANSWER_ROOT, None)


def _refuse(
    entity_class: type[Any],
    plan: EntitiesPlan,
    resource_name: str,
    entry_point: str,
    path: str,
) -> None:
    """Raise the one refusal the return check can make."""
    raise ResourceEntitiesError(
        resource_name=resource_name,
        entry_point=entry_point,
        path=path,
        entity_class=entity_class,
        declared=plan.declared,
    )


def _walk(
    value: Any,
    plan: EntitiesPlan,
    resource_name: str,
    entry_point: str,
    path: str,
    visited: set[int] | None,
) -> None:
    """Walk one value; ``visited`` breaks a cycle of loaded entities."""
    if not isinstance(value, BaseEntity):
        _walk_member(value, plan, resource_name, entry_point, path, visited)
        return
    if isinstance(value, (BaseEnumEntity, BaseStateEntity)):
        return
    entity_class = type(value)
    if not plan.declared or entity_class not in plan.listed_set:
        _refuse(entity_class, plan, resource_name, entry_point, path)
    if entity_class not in plan.leaves:
        return
    if visited is None:
        visited = set()
    if id(value) in visited:
        return
    visited.add(id(value))
    for field_name, field_value in value.__dict__.items():
        _walk(field_value, plan, resource_name, entry_point, f"{path}.{field_name}", visited)


def _walk_member(
    value: Any,
    plan: EntitiesPlan,
    resource_name: str,
    entry_point: str,
    path: str,
    visited: set[int] | None,
) -> None:
    """Walk a non-entity value: a relation container, a sequence or a mapping."""
    if isinstance(value, BaseRelationOne):
        entity = value.entity
        if entity is not None:
            _walk(entity, plan, resource_name, entry_point, path, visited)
        return
    if isinstance(value, BaseRelationMany):
        for index, entity in enumerate(value.entities):
            _walk(entity, plan, resource_name, entry_point, f"{path}[{index}]", visited)
        return
    if isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _walk(item, plan, resource_name, entry_point, f"{path}[{index}]", visited)
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            _walk(item, plan, resource_name, entry_point, f"{path}[{key}]", visited)
