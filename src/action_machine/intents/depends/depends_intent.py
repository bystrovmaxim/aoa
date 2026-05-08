# src/action_machine/intents/depends/depends_intent.py
"""
DependsIntent — marker generic mixin for ``@depends``.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``DependsIntent[T]`` is a generic mixin with two responsibilities:

1. **Marker**: the ``@depends`` decorator checks that the target class inherits
   from ``DependsIntent``. If not, a ``TypeError`` is raised. This prevents
   ``@depends`` from being applied to arbitrary classes.

2. **Type bound**: generic parameter ``T`` restricts which classes are
   allowed as dependencies. For example:
   - ``DependsIntent[object]`` — any class.
   - ``DependsIntent[DependsEligible]`` — only types that inherit
     :class:`~action_machine.intents.depends.depends_eligible.DependsEligible`
     (for example ``BaseAction`` and ``BaseResource`` in this framework).
   - ``DependsIntent[Foo | Bar]`` — any class that is a subclass of ``Foo``
     **or** of ``Bar``.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    @depends(PaymentService, description="...")
         │
         │  checks:
         ├── issubclass(cls, DependsIntent) → OK
         ├── issubclass(PaymentService, each allowed bound) → OK for at least one
         └── no duplicates → OK
         │
         ▼  writes scratch
    cls._depends_info = [DependencyInfo(PaymentService, ...)]
         │
         ▼  interchange ``DependsGraphEdge`` rows reflect ``_depends_info``
    ``ActionGraphNode`` carries dependency topology
         │
         ▼  DependencyFactory(deps); runtime reads ``_depends_info`` the same shape

"""

from __future__ import annotations

import types
from typing import Any, ClassVar, Union, get_args, get_origin


class DependsIntent[T]:
    """
    AI-CORE-BEGIN
    ROLE: Dependency declaration marker with bound metadata.
    CONTRACT: Enables ``@depends`` only for subclasses and exposes bound via ``_depends_bound``.
    INVARIANTS: Marker is runtime-light; bound is computed at class creation.
    AI-CORE-END
    """

    _depends_info: ClassVar[list[Any]]
    _depends_bound: ClassVar[Any]

    @staticmethod
    def _flatten_union_members(tp: Any) -> tuple[type, ...]:
        """
        Flatten ``X | Y | ...`` and ``typing.Union`` into a tuple of plain types.

        Unknown or non-type parameters (e.g. bare ``TypeVar``) yield an empty tuple
        so the caller can fall back to the parent bound.
        """
        if tp is Any:
            return (object,)

        origin = get_origin(tp)
        if origin is types.UnionType or origin is Union:
            members: list[type] = []
            for arg in get_args(tp):
                members.extend(DependsIntent._flatten_union_members(arg))
            seen: set[type] = set()
            unique: list[type] = []
            for t in members:
                if t not in seen:
                    seen.add(t)
                    unique.append(t)
            return tuple(unique)

        if isinstance(tp, type):
            return (tp,)

        return ()

    @staticmethod
    def _types_tuple_to_bound(types_tuple: tuple[type, ...]) -> type | types.UnionType:
        """Collapse a non-empty tuple of types into a single type or PEP 604 union."""
        if len(types_tuple) == 1:
            return types_tuple[0]
        u = types_tuple[0] | types_tuple[1]
        for t in types_tuple[2:]:
            u = u | t
        return u

    @staticmethod
    def _extract_bound(owner_cls: type) -> type | types.UnionType:
        """
        Extract the bound from ``DependsIntent[...]`` in base classes.

        Walks ``owner_cls.__orig_bases__`` looking for ``DependsIntent[X]``. ``X``
        may be a single type or a union of types. Otherwise falls back to the
        parent's bound or ``object``.
        """
        for base in getattr(owner_cls, "__orig_bases__", ()):
            origin = get_origin(base)
            if origin is not DependsIntent:
                continue
            args = get_args(base)
            if not args:
                return object
            flat = DependsIntent._flatten_union_members(args[0])
            if flat:
                return DependsIntent._types_tuple_to_bound(flat)

        for parent in owner_cls.__mro__[1:]:
            bound = getattr(parent, "_depends_bound", None)
            if bound is not None:
                return bound  # type: ignore[no-any-return]

        return object

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """
        Extract the bound type from the generic parameter and store it.

        Called by Python when a subclass of ``DependsIntent`` is created.
        """
        super().__init_subclass__(**kwargs)
        cls._depends_bound = DependsIntent._extract_bound(cls)

    @classmethod
    def get_depends_bound(cls) -> Any:
        """Return the bound for ``issubclass`` checks (a type or a ``types.UnionType``)."""
        return getattr(cls, "_depends_bound", object)

    @classmethod
    def get_depends_bounds(cls) -> tuple[type, ...]:
        """Return allowed dependency types as a flat tuple (after union expansion)."""
        return DependsIntent._flatten_union_members(cls.get_depends_bound())
