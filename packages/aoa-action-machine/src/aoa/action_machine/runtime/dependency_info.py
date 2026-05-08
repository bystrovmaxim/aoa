# packages/aoa-action-machine/src/aoa/action_machine/runtime/dependency_info.py
"""
``DependencyInfo`` — immutable record for one ``@depends`` declaration.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Holds the dependency class, optional factory override, and description written
by the ``@depends`` decorator. The list is stored as ``cls._depends_info``; runtime
:class:`~aoa.action_machine.runtime.dependency_factory.DependencyFactory` consumes it.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DependencyInfo:
    """
    Immutable information about a single action dependency.

    Created by the ``@depends`` decorator and stored on ``cls._depends_info``.
    :class:`~aoa.action_machine.runtime.dependency_factory.DependencyFactory` reads this tuple during ``ToolsBox`` construction.

    Attributes:
        cls: The dependency class (type requested via ``box.resolve``).
        factory: Optional factory callable for creating the instance.
                 If ``None``, the default constructor ``klass()`` is used.
                 Use a lambda for singletons, e.g. ``lambda: shared_instance``.
        description: Human‑readable description for documentation and introspection.
    """
    cls: type
    factory: Callable[..., Any] | None = None
    description: str = ""
