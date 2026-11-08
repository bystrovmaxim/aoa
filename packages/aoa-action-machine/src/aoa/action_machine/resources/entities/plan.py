# packages/aoa-action-machine/src/aoa/action_machine/resources/entities/plan.py
"""
EntitiesPlan — what the return check of one resource was computed to do.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A resource **is** a database: ``@entities(*classes)`` lists the entities that lie in
it and that the resource may return. The machine checks every public method's answer
against that list, and this module freezes what the check needs before any call:

1. **The listed classes** — the classes the resource declared, in declaration order,
   read from the concrete class's own ``_entities_info``.
2. **Who can leave the list** — for each listed class, whether a relation reachable
   from it leads to a class outside the list. A class from which no such relation is
   reachable needs only its type checked; walking its fields would find nothing.
3. **Whether the resource declares ``@entities`` at all** — a resource without the
   declaration refuses every entity it returns, saying so; an empty declaration
   refuses them because the list is empty.

The plan is **frozen data** kept in the concrete class's own ``__dict__``:
``cls.__dict__['_entities_plan']``. It is never inherited — a subclass resource
states what its own database holds, and a subclass without ``@entities`` refuses
every entity instead of borrowing its parent's list. The wrapper always looks the
plan up for ``type(self)``.

═══════════════════════════════════════════════════════════════════════════════
WHEN IT IS COMPUTED
═══════════════════════════════════════════════════════════════════════════════

- :meth:`~aoa.action_machine.graph.core.node_graph_coordinator.NodeGraphCoordinator.build`
  calls :func:`attach_entities_plans` for every resource node the graph carries. A
  broken declaration fails with the model, not with the first request.
- The first public call on a resource used without a machine (a unit test, a script)
  computes it lazily through :func:`entities_plan_for_instance` and attaches it.

═══════════════════════════════════════════════════════════════════════════════
A WRAPPER ANSWERS BY THE PLAN OF THE RESOURCE IT WRAPS
═══════════════════════════════════════════════════════════════════════════════

A per-kind nesting wrapper (``SqlStorageWrapper``, ``OcelStorageWrapper``, an
application's ``…StorageWrapper``) has no ``@entities`` of its own; it hands a nested
action the resource it wraps. Its answers are checked by **that resource's** plan.
:func:`entities_plan_for_instance` recognises a wrapper by the naming rule every
wrapper already obeys (its name ends with ``Wrapper``) and reads the wrapped resource
from the instance — the same object the wrapper delegates to.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    cls.__dict__['_entities_info']  +  entity relation metadata of each listed class
                     │
                     ▼
    compute_entities_plan(cls) → EntitiesPlan(declared, listed, leaves)
                     │
                     ├─ NodeGraphCoordinator.build → attach_entities_plans(...)
                     └─ first public call        → entities_plan_for_instance(instance)

"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from aoa.action_machine.domain.enum_entity import BaseEnumEntity
from aoa.action_machine.domain.state_entity import BaseStateEntity
from aoa.action_machine.intents.entities.entities_decorator import entities_info_tuple
from aoa.action_machine.intents.entities.entities_intent import entities_info_is_set
from aoa.action_machine.intents.entity.entity_relation_intent_resolver import (
    gather_entity_relation_intent_resolvers,
)

__all__ = [
    "PLAN_ATTRIBUTE",
    "EntitiesPlan",
    "attach_entities_plans",
    "compute_entities_plan",
    "entities_plan_for_class",
    "entities_plan_for_instance",
    "is_wrapper_class",
    "wrapped_resource_of",
]

PLAN_ATTRIBUTE = "_entities_plan"
"""The name a concrete resource class keeps its frozen plan under, in its own ``__dict__``."""

_WRAPPED_ATTRIBUTE_NAMES = ("_connection_manager", "_resource", "_storage", "_inner")
"""Attribute names the framework's own wrappers store the wrapped resource under, in lookup order."""


@dataclass(frozen=True)
class EntitiesPlan:
    """
    AI-CORE-BEGIN
    ROLE: Frozen data the return check of one concrete resource class applies to an answer.
    CONTRACT: Holds the resource name, whether ``@entities`` was declared, the listed classes and
        the listed classes from which a reachable relation leads outside the list.
    INVARIANTS: Built once per concrete class and stored in ``cls.__dict__``; never inherited and
        never mutated. A class in ``leaves`` may be refused through a loaded relation; a listed
        class outside it needs only its exact type checked.
    AI-CORE-END
    """

    resource_name: str
    """The concrete resource class name, as the refusal names it."""

    declared: bool
    """``True`` when the concrete class declared ``@entities`` in its own body."""

    listed: tuple[type[Any], ...]
    """The listed entity classes, in declaration order."""

    listed_set: frozenset[type[Any]]
    """The same classes as a set, for exact-class membership checks on the hot path."""

    leaves: frozenset[type[Any]]
    """Listed classes from which a reachable relation leads outside the list (need a walk)."""

    def lists(self, entity_cls: type[Any]) -> bool:
        """Return ``True`` when the resource lists ``entity_cls`` exactly."""
        return entity_cls in self.listed_set

    def needs_walk(self, entity_cls: type[Any]) -> bool:
        """Return ``True`` when fields of ``entity_cls`` must be walked to find an outside class."""
        return entity_cls in self.leaves


def _is_model_owned(entity_cls: type[Any]) -> bool:
    """True for a dictionary member or a lifecycle state: the model's, not a database's."""
    return issubclass(entity_cls, (BaseEnumEntity, BaseStateEntity))


def _relation_targets(entity_cls: type[Any]) -> tuple[type[Any], ...]:
    """
    Return the entity classes ``entity_cls`` reaches through relation-container fields.

    Dictionary members and lifecycle states are left out: a relation to a dictionary
    holds its members loaded by design, and neither belongs to a database, so neither
    is a way out of the list.
    """
    targets: list[type[Any]] = []
    for row in gather_entity_relation_intent_resolvers(entity_cls):
        target = row.target_entity
        if isinstance(target, type) and not _is_model_owned(target):
            targets.append(target)
    return tuple(targets)


def _reaches_outside(
    start: type[Any],
    targets_of: dict[type[Any], tuple[type[Any], ...]],
    listed: frozenset[type[Any]],
) -> bool:
    """True when a relation reachable from ``start`` lands on a class outside ``listed``."""
    seen = {start}
    stack = [start]
    while stack:
        for target in targets_of.get(stack.pop(), ()):
            if target not in listed:
                return True
            if target not in seen:
                seen.add(target)
                stack.append(target)
    return False


def compute_entities_plan(resource_cls: type[Any]) -> EntitiesPlan:
    """
    Compute the frozen plan of one concrete resource class from its own declaration.

    Args:
        resource_cls: A resource class. Only its own ``_entities_info`` counts; a list
            inherited from a parent is not its own.

    Returns:
        The plan: whether ``@entities`` was declared, the listed classes, and the listed
        classes from which a reachable relation leads outside the list.
    """
    listed = entities_info_tuple(resource_cls)
    declared = entities_info_is_set(resource_cls)
    listed_set = frozenset(listed)
    targets_of = {entity_cls: _relation_targets(entity_cls) for entity_cls in listed}
    leaves = frozenset(
        entity_cls for entity_cls in listed if _reaches_outside(entity_cls, targets_of, listed_set)
    )
    return EntitiesPlan(
        resource_name=resource_cls.__name__,
        declared=declared,
        listed=listed,
        listed_set=listed_set,
        leaves=leaves,
    )


def attach_entities_plans(resource_classes: Iterable[type[Any]]) -> None:
    """
    Compute and attach the plan to each resource class; called by ``NodeGraphCoordinator.build``.

    The plan is recomputed even when a lazy call already attached one: a build is the
    moment the model's declaration is authoritative.
    """
    seen: set[int] = set()
    for resource_cls in resource_classes:
        if not isinstance(resource_cls, type) or id(resource_cls) in seen:
            continue
        seen.add(id(resource_cls))
        setattr(resource_cls, PLAN_ATTRIBUTE, compute_entities_plan(resource_cls))


def entities_plan_for_class(resource_cls: type[Any]) -> EntitiesPlan:
    """
    Return the plan of ``resource_cls``, computing and attaching it on first use.

    Only the class's own ``__dict__`` is read: a subclass never inherits a parent's
    plan, because it states what its own database holds.
    """
    plan = resource_cls.__dict__.get(PLAN_ATTRIBUTE)
    if isinstance(plan, EntitiesPlan):
        return plan
    plan = compute_entities_plan(resource_cls)
    setattr(resource_cls, PLAN_ATTRIBUTE, plan)
    return plan


def is_wrapper_class(cls: type[Any]) -> bool:
    """True when ``cls`` is a per-kind nesting wrapper (its name ends with ``Wrapper``)."""
    return cls.__name__.endswith("Wrapper")


def _is_resource(value: Any) -> bool:
    """True when ``value`` is a ``BaseResource`` instance; imported late to avoid a cycle."""
    # Late import: ``BaseResource`` imports this package's intent marker.
    from aoa.action_machine.resources.base_resource import BaseResource  # pylint: disable=import-outside-toplevel

    return isinstance(value, BaseResource)


def wrapped_resource_of(instance: Any) -> Any | None:
    """
    Return the resource a wrapper instance wraps, or ``None``.

    Only a wrapper (a resource whose name ends with ``Wrapper``) is looked into. Known
    attribute names the framework's wrappers use are searched first; then any
    ``BaseResource`` held in the instance's ``__dict__`` answers.
    """
    if not is_wrapper_class(type(instance)):
        return None
    namespace = getattr(instance, "__dict__", {})
    if not isinstance(namespace, dict):
        return None
    for name in _WRAPPED_ATTRIBUTE_NAMES:
        candidate = namespace.get(name)
        if candidate is not instance and _is_resource(candidate):
            return candidate
    for candidate in namespace.values():
        if candidate is not instance and _is_resource(candidate):
            return candidate
    return None


def _wrapper_plan(instance: Any, seen: frozenset[int]) -> EntitiesPlan:
    """Resolve a wrapper's plan from the resource it wraps, guarding a wrapper chain cycle."""
    if id(instance) in seen:
        return entities_plan_for_class(type(instance))
    wrapped = wrapped_resource_of(instance)
    if wrapped is None:
        return entities_plan_for_class(type(instance))
    if is_wrapper_class(type(wrapped)):
        return _wrapper_plan(wrapped, seen | {id(instance)})
    return entities_plan_for_class(type(wrapped))


def entities_plan_for_instance(instance: Any) -> EntitiesPlan:
    """
    Return the plan that governs ``instance``'s answers.

    A plain resource uses the plan of its concrete class. A per-kind nesting wrapper
    answers by the plan of the resource it wraps; a wrapper that holds no resource
    falls back to its own class's plan.
    """
    cls = type(instance)
    if not is_wrapper_class(cls):
        plan = cls.__dict__.get(PLAN_ATTRIBUTE)
        if isinstance(plan, EntitiesPlan):
            return plan
        return entities_plan_for_class(cls)
    return _wrapper_plan(instance, frozenset())
