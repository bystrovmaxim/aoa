# src/action_machine/dependencies/dependency_intent.py
"""
DependencyIntent — marker generic mixin for ``@depends``.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``DependencyIntent[T]`` is a generic mixin with two responsibilities:

1. **Marker**: the ``@depends`` decorator checks that the target class inherits
   from ``DependencyIntent``. If not, a ``TypeError`` is raised. This prevents
   ``@depends`` from being applied to arbitrary classes.

2. **Type bound**: generic parameter ``T`` restricts which classes are
   allowed as dependencies. For example:
   - ``DependencyIntent[object]`` — any class.
   - ``DependencyIntent[BaseResourceManager]`` — only resource managers.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    @depends(PaymentService, description="...")
         │
         │  checks:
         ├── issubclass(cls, DependencyIntent) → OK
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

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- ``@depends`` can only be applied to classes that inherit ``DependencyIntent``.
- Bound type ``T`` is extracted from the generic parameter at class creation
  and stored in ``cls._depends_bound``.
- The decorator validates that each declared dependency is a subclass of this bound.
- ``_depends_info`` is a list of ``DependencyInfo`` instances; duplicates are
  forbidden.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    # Allow any dependency
    class MyAction(DependencyIntent[object]):
        pass

    # Restrict dependencies to resource managers only
    class ResourcePool(DependencyIntent[BaseResourceManager]):
        pass

    @depends(PostgresManager)   # OK — PostgresManager < BaseResourceManager
    @depends(PaymentService)    # TypeError — PaymentService is not a BaseResourceManager
    class MyPool(ResourcePool):
        ...

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- ``TypeError`` if ``@depends`` is applied to a class without ``DependencyIntent``
  or if a dependency does not satisfy the bound.
- The bound extraction relies on ``__orig_bases__`` and may fail for complex
  generic aliases; in such cases it falls back to ``object``.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Intent marker for dependency declarations.
CONTRACT: Subclass required for ``@depends``; provides bound type for validation.
INVARIANTS: Pure marker; bound stored in ``_depends_bound``.
FLOW: decorator checks marker and bound → writes scratch → inspector consumes.
FAILURES: TypeError on missing marker or bound violation.
EXTENSION POINTS: Bound can be customized via generic parameter.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from typing import Any, ClassVar, get_args, get_origin


class DependencyIntent[T]:
    """
    Marker generic mixin that enables ``@depends`` usage.

    Classes that do not inherit from ``DependencyIntent`` cannot be decorated
    with ``@depends`` — a ``TypeError`` is raised.

    Generic parameter ``T`` defines the upper bound for allowed dependency
    types. The decorator verifies that each declared dependency is a subclass
    of this bound.

    Class attributes (created dynamically):
        _depends_info : list[DependencyInfo]
            Temporary list populated by ``@depends``; read by the inspector.
        _depends_bound : type
            The bound type extracted from the generic parameter.

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

        Called by Python when a subclass of ``DependencyIntent`` is created.
        """
        super().__init_subclass__(**kwargs)
        cls._depends_bound = _extract_bound(cls)

    @classmethod
    def get_depends_bound(cls) -> type:
        """Return the bound type for dependencies of this class (default: ``object``)."""
        return getattr(cls, "_depends_bound", object)


def _extract_bound(cls: type) -> type:
    """
    Extract the bound type ``T`` from ``DependencyIntent[T]`` in base classes.

    Walks ``cls.__orig_bases__`` looking for ``DependencyIntent[X]``. If ``X`` is
    a concrete type, returns it. Otherwise falls back to the parent's bound or
    ``object``.
    """
    for base in getattr(cls, "__orig_bases__", ()):
        origin = get_origin(base)
        if origin is DependencyIntent:
            args = get_args(base)
            if args and isinstance(args[0], type):
                return args[0]

    for parent in cls.__mro__[1:]:
        bound = getattr(parent, "_depends_bound", None)
        if bound is not None:
            return bound  # type: ignore[no-any-return]

    return object
