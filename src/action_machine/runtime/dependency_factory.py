# src/action_machine/runtime/dependency_factory.py
"""
DependencyFactory — stateless dependency resolution and cache helpers.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provide a stateless factory that creates dependency instances declared via
``@depends``. The factory is built from ``DependencyInfo`` snapshots obtained
from ``GraphCoordinator``. Each call to ``resolve()`` creates a new instance
(no internal instance cache). The module also provides a coordinator-level cache
helper for factory reuse.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from action_machine.resources.base_resource import BaseResource
from action_machine.runtime.dependency_info import DependencyInfo

if TYPE_CHECKING:
    from graph.graph_coordinator import GraphCoordinator


class DependencyFactory:
    """
AI-CORE-BEGIN
    ROLE: Stateless constructor/validator for declared dependencies.
    CONTRACT: Resolve only declared classes, with optional factory override and rollup checks.
    INVARIANTS: No instance reuse inside the factory; ``_deps`` is built once and read-only by convention.
    AI-CORE-END
"""

    def __init__(self, dependencies: tuple[Any, ...] | list[dict[str, Any]]) -> None:
        """
        Initialize the factory.

        Args:
            dependencies:
                - ``tuple[DependencyInfo, ...]`` — primary format (from the
                  coordinator ``depends`` snapshot).
                - ``list[dict]`` — backward compatibility for tests.
                  Each dict: ``{"class": type, "factory": callable|None,
                  "description": str}``
        """
        if isinstance(dependencies, (tuple, list)) and dependencies and isinstance(dependencies[0], dict):
            self._deps: dict[type, DependencyInfo] = self._build_from_dicts(list(dependencies))
        else:
            self._deps = self._build_from_infos(dependencies)

    @staticmethod
    def _build_from_infos(infos: tuple[Any, ...] | list[Any]) -> dict[type, DependencyInfo]:
        """Build a mapping from a tuple of DependencyInfo."""
        result: dict[type, DependencyInfo] = {}
        for info in infos:
            result[info.cls] = info
        return result

    @staticmethod
    def _build_from_dicts(dicts: list[dict[str, Any]]) -> dict[type, DependencyInfo]:
        """Build a mapping from a list of dicts (backward compatibility)."""
        result: dict[type, DependencyInfo] = {}
        for info_dict in dicts:
            info = DependencyInfo(
                cls=info_dict["class"],
                factory=info_dict.get("factory"),
                description=info_dict.get("description", ""),
            )
            result[info.cls] = info
        return result

    def resolve(self, klass: type, *args: Any, rollup: bool = False, **kwargs: Any) -> Any:
        """
        Create and return a new dependency instance.

        Each call creates a fresh object. No caching is performed.

        Steps:
            1. Look up ``DependencyInfo`` by class.
            2. If ``info.factory`` is set, call ``info.factory(*args, **kwargs)``.
            3. Otherwise, call ``klass(*args, **kwargs)``.
            4. If ``rollup=True`` and the result is a ``BaseResource``,
               call ``instance.check_rollup_support()``.

        Args:
            klass: Dependency class (the same as passed to ``@depends``).
            *args: Positional arguments for the factory or constructor.
            rollup: If ``True``, verify rollup support for ``BaseResource``
                    instances. Defaults to ``False``.
            **kwargs: Keyword arguments for the factory or constructor.

        Returns:
            A new dependency instance.

        Raises:
            ValueError: If the dependency was not declared via ``@depends``.
            RollupNotSupportedError: If ``rollup=True`` and the instance is a
                ``BaseResource`` that does not support rollup.
        """
        info = self._deps.get(klass)
        if info is None:
            available = list(self._deps.keys())
            raise ValueError(
                f"Dependency {klass.__name__} not declared in @depends. "
                f"Available: {available}"
            )

        if info.factory:
            instance = info.factory(*args, **kwargs)
        else:
            instance = klass(*args, **kwargs)

        if rollup and isinstance(instance, BaseResource):
            instance.check_rollup_support()

        return instance

    def get_all_classes(self) -> list[type]:
        """Return a list of all registered dependency classes."""
        return list(self._deps.keys())

    def has(self, klass: type) -> bool:
        """Return ``True`` if a dependency is declared for the given class."""
        return klass in self._deps


DEPENDENCY_FACTORY_CACHE_KEY = "_action_machine_dependency_factory_cache"


def cached_dependency_factory(
    coordinator: GraphCoordinator,
    cls: type,
) -> DependencyFactory:
    """
    Return (and cache on the coordinator) the ``DependencyFactory`` for an action
    class, using its ``depends`` snapshot.
    """
    if not coordinator.is_built:
        raise RuntimeError(
            "GraphCoordinator is not built. Register inspectors and call build() first.",
        )
    cache: dict[type, DependencyFactory] = coordinator.__dict__.setdefault(
        DEPENDENCY_FACTORY_CACHE_KEY,
        {},
    )
    if cls not in cache:
        snap = coordinator.get_snapshot(cls, "depends")
        if snap is not None and hasattr(snap, "dependencies"):
            deps = snap.dependencies
        else:
            deps = ()
        cache[cls] = DependencyFactory(deps)
    return cache[cls]
