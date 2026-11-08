# packages/aoa-action-machine/src/aoa/action_machine/resources/base_resource.py
"""
BaseResource — declaration contract for managed resources.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A resource manager is any object that controls an external resource
(database connection, cache, queue, and so on) and is passed into action
aspects through the ``connections`` mapping.

Each resource manager must provide a wrapper class used when the resource is
propagated to child actions. The wrapper blocks lifecycle control
(``open/begin/commit/rollback``) but allows execution operations.

═══════════════════════════════════════════════════════════════════════════════
REQUIRED @meta DECORATOR AND OPTIONAL @entities
═══════════════════════════════════════════════════════════════════════════════

Every resource manager must declare ``@meta(...)`` with a description and **no**
domain: a resource is a database shared by domains, so its domains are the domains
of the entities it lists with ``@entities(...)``. This is enforced through
``MetaIntent`` and ``EntitiesIntent`` in ``BaseResource`` inheritance.

═══════════════════════════════════════════════════════════════════════════════
THE RETURN CHECK
═══════════════════════════════════════════════════════════════════════════════

A resource may return only the entities its ``@entities`` lists. When a resource
class is declared, ``__init_subclass__`` wraps each public plain function, coroutine
function and async generator of its class body exactly once
(:func:`wrap_public_methods`): the answer is walked by
:func:`~aoa.action_machine.resources.entities.walk.walk_answer` against the frozen
plan of the concrete class that answered
(:mod:`~aoa.action_machine.resources.entities.plan`), and an entity outside the list
raises ``ResourceEntitiesError``. Names starting with ``_``, class methods, static
methods, properties and plain generators are left untouched. The action still
receives the resource itself, so ``isinstance``, identity and attribute access are
unchanged — ``connections[…]``, ``box.resolve(…)`` and a test-bench substitute all
reach the same object and are checked by its own methods.

═══════════════════════════════════════════════════════════════════════════════
ROLLUP SUPPORT
═══════════════════════════════════════════════════════════════════════════════

Rollup mode enables safe execution against production-like data: writes run in
transaction scope, but commit stage performs rollback instead of persist.

``check_rollup_support()`` defines whether the concrete manager supports rollup.
Default implementation raises ``RollupNotSupportedError``. Managers that support
rollup (for example SQL managers) override the method.

When ``DependencyFactory.resolve(..., rollup=True)`` builds managers, it calls
``check_rollup_support()`` for each ``BaseResource`` instance and fails
fast on unsupported resources.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    class BaseResource(ABC, MetaIntent, EntitiesIntent, DependsEligible):
        check_rollup_support() → raises RollupNotSupportedError
        get_wrapper_class()    → type | None

    class SqlStorage(BaseStorage):
        check_rollup_support() → True  (overrides, supports rollup)
        __init__(rollup=False)         (accepts rollup flag)
        commit()                       (with rollup=True -> rollback instead of commit)

    @meta(description="PostgreSQL manager")
    @entities(OrderCoreEntity, CustomerCoreEntity)
    class PostgresStorage(SqlStorage):
        __init__(params, rollup=False) (passes rollup to super)

    @meta(description="Redis cache manager")
    class RedisStorage(BaseStorage):
        check_rollup_support()         (not overridden -> RollupNotSupportedError)

"""

import functools
import inspect
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any, cast

from aoa.action_machine.exceptions.declaration_structure_error import DeclarationStructureError
from aoa.action_machine.exceptions.naming_suffix_error import NamingSuffixError
from aoa.action_machine.exceptions.rollup_not_supported_error import RollupNotSupportedError
from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.intents.depends.depends_eligible import DependsEligible
from aoa.action_machine.intents.entities.entities_intent import EntitiesIntent
from aoa.action_machine.intents.meta.meta_intent import MetaIntent


@exclude_graph_model
class BaseResource(ABC, MetaIntent, EntitiesIntent, DependsEligible):
    """
    A managed resource belongs to one kind, declares its wrapper without an instance,
    and may list the entities of its database with ``@entities``.

    AI-CORE-BEGIN
    ROLE: Root of managed long-lived dependencies.
    CONTRACT: Concrete resources inherit a canonical kind and declare wrappers through a class method.
    INVARIANTS: Exactly one ancestry-derived kind; a resource has no domain of its own.
    AI-CORE-END
    """

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Validate resource kind and name declarations, then wrap the class's public methods."""
        super().__init_subclass__(**kwargs)
        _check_resource_kind(cls)
        wrap_public_methods(cls)

    async def check_rollup_support(self) -> bool:
        """
        Check whether this manager supports rollup transaction mode.

        Default behavior raises ``RollupNotSupportedError``; rollup-capable
        managers override and return ``True``.
        """
        raise RollupNotSupportedError(
            f"Class '{type(self).__name__}' does not support rollup. "
            f"Implement check_rollup_support() or use a resource manager "
            f"that supports transactional rollback."
        )

    @classmethod
    @abstractmethod
    def get_wrapper_class(cls) -> type["BaseResource"] | None:
        """Return a wrapper class, or ``None`` for direct pass-through."""
        pass


PUBLIC_METHOD_MARKER = "__aoa_entities_wrapped__"
"""Marker set on a method already wrapped by :func:`wrap_public_methods`; keeps the wrapping idempotent."""


def _checked_answer(
    instance: Any,
    answer: Any,
    entry_point: str,
    entities_plan_for_instance: Callable[[Any], Any],
    walk_answer: Callable[..., None],
) -> None:
    """Walk one answer by the plan of the resource that answered."""
    plan = entities_plan_for_instance(instance)
    walk_answer(answer, plan, plan.resource_name, entry_point, "")


def _wrap_plain_function(
    func: Callable[..., Any],
    entry_point: str,
    entities_plan_for_instance: Callable[[Any], Any],
    walk_answer: Callable[..., None],
) -> Callable[..., Any]:
    """Wrap a plain function: walk the answer it returns, unchanged."""

    @functools.wraps(func)
    def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        answer = func(self, *args, **kwargs)
        _checked_answer(self, answer, entry_point, entities_plan_for_instance, walk_answer)
        return answer

    _mark_wrapped(wrapper, func)
    return wrapper


def _wrap_coroutine_function(
    func: Callable[..., Any],
    entry_point: str,
    entities_plan_for_instance: Callable[[Any], Any],
    walk_answer: Callable[..., None],
) -> Callable[..., Any]:
    """Wrap a coroutine function: await the answer, walk it, return it unchanged."""

    @functools.wraps(func)
    async def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        answer = await func(self, *args, **kwargs)
        _checked_answer(self, answer, entry_point, entities_plan_for_instance, walk_answer)
        return answer

    _mark_wrapped(wrapper, func)
    return wrapper


def _wrap_async_generator_function(
    func: Callable[..., Any],
    entry_point: str,
    entities_plan_for_instance: Callable[[Any], Any],
    walk_answer: Callable[..., None],
) -> Callable[..., Any]:
    """Wrap an async generator: check each element as it yields."""

    @functools.wraps(func)
    async def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        async for element in func(self, *args, **kwargs):
            _checked_answer(self, element, entry_point, entities_plan_for_instance, walk_answer)
            yield element

    _mark_wrapped(wrapper, func)
    return wrapper


def _mark_wrapped(wrapper: Callable[..., Any], original: Callable[..., Any]) -> None:
    """Mark a wrapper idempotently, and keep an abstract method's abstractness."""
    setattr(wrapper, PUBLIC_METHOD_MARKER, True)
    if getattr(original, "__isabstractmethod__", False):
        # ``Callable`` has no typed dunder slot; the attribute is what marks a method abstract.
        cast(Any, wrapper).__isabstractmethod__ = True


def wrap_public_methods(cls: type) -> None:
    """
    Wrap each public function declared in ``cls``'s class body exactly once.

    A plain function walks its answer, a coroutine function awaits and walks it, and
    an async generator checks every element as it yields. Names starting with ``_``
    are left alone, and so are class methods, static methods and properties — they
    are descriptors, not functions. A plain generator is left alone (a wrapper cannot
    see through it without running it), and a plain function that returns an
    awaitable is not awaited, so the answer behind it is unchecked.

    The wrapper reads the plan of the concrete resource that answered, so a subclass
    with its own ``@entities`` is checked by its own list and a nesting wrapper is
    checked by the plan of the resource it wraps. It is attached to the class
    attribute, so the action still receives the resource itself: ``isinstance``,
    identity and attribute access are unchanged.
    """
    # Imported here: the plan module reads this module's intent marker through the package.
    from aoa.action_machine.resources.entities.plan import entities_plan_for_instance  # pylint: disable=import-outside-toplevel
    from aoa.action_machine.resources.entities.walk import walk_answer  # pylint: disable=import-outside-toplevel

    for name, member in list(cls.__dict__.items()):
        if name.startswith("_") or getattr(member, PUBLIC_METHOD_MARKER, False):
            continue
        if not inspect.isfunction(member):
            continue
        if inspect.isasyncgenfunction(member):
            wrapper = _wrap_async_generator_function(
                member, name, entities_plan_for_instance, walk_answer
            )
        elif inspect.iscoroutinefunction(member):
            wrapper = _wrap_coroutine_function(member, name, entities_plan_for_instance, walk_answer)
        elif inspect.isgeneratorfunction(member):
            continue
        else:
            wrapper = _wrap_plain_function(member, name, entities_plan_for_instance, walk_answer)
        setattr(cls, name, wrapper)


_KIND_BASES = "BaseStorage, BaseGateway or BaseController"
_KIND_DECLARATIONS = {
    ("aoa.action_machine.resources.base_storage", "BaseStorage"): "Storage",
    ("aoa.action_machine.resources.base_gateway", "BaseGateway"): "Gateway",
    ("aoa.action_machine.resources.base_controller", "BaseController"): "Controller",
}
_KIND_TYPES: dict[type, str] = {}


def resource_kind(cls: type) -> str:
    """
    Return the resource kind established by framework ancestry.

    AI-CORE-BEGIN
    ROLE: Resolve a resource's canonical kind.
    CONTRACT: Return Storage, Gateway or Controller from registered base identities.
    INVARIANTS: Descendant attributes cannot change kind; mixed kinds are refused.
    AI-CORE-END
    """
    kinds = {_KIND_TYPES[base] for base in cls.__mro__ if base in _KIND_TYPES}
    if len(kinds) != 1:
        raise DeclarationStructureError(
            f"Class '{cls.__name__}' inherits {len(kinds)} resource kinds: a resource inherits exactly one of {_KIND_BASES}."
        )
    return next(iter(kinds))


def _check_resource_kind(cls: type) -> None:
    """Admit canonical kind bases and validate every descendant's name."""
    if BaseResource in cls.__bases__:
        declaration = (cls.__module__, cls.__qualname__)
        kind = _KIND_DECLARATIONS.get(declaration)
        # Each canonical declaration registers once during framework import.
        if kind is not None and kind not in _KIND_TYPES.values():
            _KIND_TYPES[cls] = kind
            return
        raise DeclarationStructureError(
            f"Class '{cls.__name__}' inherits BaseResource directly. "
            f"A resource inherits one of the three kind base classes instead: {_KIND_BASES}."
        )
    kind = resource_kind(cls)
    name = cls.__name__
    if name.endswith("Wrapper"):
        if not name.endswith(f"{kind}Wrapper"):
            raise NamingSuffixError(
                f"Class '{name}' is a wrapper of a Base{kind} and lacks the '{kind}Wrapper' suffix. "
                f"Rename to '{name.removesuffix('Wrapper')}{kind}Wrapper'."
            )
    elif not name.endswith(kind):
        raise NamingSuffixError(f"Class '{name}' inherits Base{kind} but lacks the '{kind}' suffix. Rename to '{name}{kind}'.")
