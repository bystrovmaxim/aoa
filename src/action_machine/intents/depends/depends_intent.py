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
   - ``DependsIntent[BaseResource]`` — only resource managers.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    @depends(PaymentService, description="...")
         │
         │  checks:
         ├── issubclass(cls, DependsIntent) → OK
         ├── issubclass(PaymentService, cls._depends_bound) → OK
         └── no duplicates → OK
         │
         ▼  writes scratch
    cls._depends_info = [DependencyInfo(PaymentService, ...)]
         │
         ▼  DependencyIntentInspector reads _depends_info
    coordinator snapshot → tuple[DependencyInfo, ...]
         │
         ▼  cached_dependency_factory(coordinator, cls)
    DependencyFactory built from snapshot

"""

from __future__ import annotations

from typing import Any, ClassVar, get_args, get_origin


class DependsIntent[T]:
    """
    AI-CORE-BEGIN
    ROLE: Dependency declaration marker with bound metadata.
    CONTRACT: Enables ``@depends`` only for subclasses and exposes bound via ``_depends_bound``.
    INVARIANTS: Marker is runtime-light; bound is computed at class creation.
    AI-CORE-END
    """

    _depends_info: ClassVar[list[Any]]
    _depends_bound: ClassVar[type]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """
        Extract the bound type from the generic parameter and store it.

        Called by Python when a subclass of ``DependsIntent`` is created.
        """
        super().__init_subclass__(**kwargs)
        cls._depends_bound = _extract_bound(cls)

    @classmethod
    def get_depends_bound(cls) -> type:
        """Return the bound type for dependencies of this class (default: ``object``)."""
        return getattr(cls, "_depends_bound", object)


def _extract_bound(cls: type) -> type:
    """
    Extract the bound type ``T`` from ``DependsIntent[T]`` in base classes.

    Walks ``cls.__orig_bases__`` looking for ``DependsIntent[X]``. If ``X`` is
    a concrete type, returns it. Otherwise falls back to the parent's bound or
    ``object``.
    """
    for base in getattr(cls, "__orig_bases__", ()):
        origin = get_origin(base)
        if origin is DependsIntent:
            args = get_args(base)
            if args and isinstance(args[0], type):
                return args[0]

    for parent in cls.__mro__[1:]:
        bound = getattr(parent, "_depends_bound", None)
        if bound is not None:
            return bound  # type: ignore[no-any-return]

    return object
