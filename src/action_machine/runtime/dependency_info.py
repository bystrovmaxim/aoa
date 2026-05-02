# src/action_machine/runtime/dependency_info.py
"""
``DependencyInfo`` — immutable record for one ``@depends`` declaration.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Holds the dependency class, optional factory override, and description written
by the ``@depends`` decorator. Inspectors read ``cls._depends_info`` lists of
these objects;
:class:`~action_machine.runtime.dependency_factory.DependencyFactory`
consumes tuples of ``DependencyInfo`` from ``cls._depends_info``.
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
    The ``DependencyIntentInspector`` derives facet rows from this data; the runtime    ``DependencyFactory`` consumes this tuple directly in the machine.

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
