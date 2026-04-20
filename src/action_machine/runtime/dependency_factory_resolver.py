# src/action_machine/runtime/dependency_factory_resolver.py
"""
Protocol for resolving ``DependencyFactory`` from an action class.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Define a **public** structural contract used by ``ToolsBoxFactory`` to obtain a
``DependencyFactory`` for a given action type without reaching into private
attributes of ``ActionProductMachine``.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    ActionProductMachine (implements DependencyFactoryResolver)
        │
        │  dependency_factory_for(action_cls)  ──► DependencyFactory
        │
        ▼
    ToolsBoxFactory.create(factory_resolver=self, ...)
        │
        └── ScopedLogger + ToolsBox(factory=resolver.dependency_factory_for(...))

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path:
    Production machine passes ``self`` into factory ``create(...)`` and exposes
    public ``dependency_factory_for``.

Edge case:
    Tests pass a stub object or ``MagicMock(spec_set=...)`` implementing only
    ``dependency_factory_for``.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Decouple toolbox factory from machine private fields.
CONTRACT: dependency_factory_for(action_cls) -> DependencyFactory.
INVARIANTS: structural Protocol; no runtime registration.
FLOW: factory.create receives resolver -> one call per ToolsBox build.
FAILURES: delegated to implementation.
EXTENSION POINTS: custom resolver for tests or alternate DI graphs.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from typing import Protocol

from action_machine.runtime.dependency_factory import DependencyFactory


class DependencyFactoryResolver(Protocol):
    """
    Public resolver hook for ``DependencyFactory`` per action class.

    AI-CORE-BEGIN
    ROLE: Narrow DI surface for ``ToolsBoxFactory``.
    CONTRACT: One method, stable name ``dependency_factory_for``.
    INVARIANTS: No state requirements beyond implementation needs.
    AI-CORE-END
    """

    def dependency_factory_for(self, action_cls: type) -> DependencyFactory:
        """Return the dependency factory to use when running ``action_cls``."""
        pass
