# src/action_machine/intents/depends/__init__.py
"""Class-level ``@depends`` decorator for ``DependencyIntent``."""

from action_machine.intents.depends.dependency_intent import DependencyIntent
from action_machine.intents.depends.depends_decorator import depends

__all__ = ["DependencyIntent", "depends"]
