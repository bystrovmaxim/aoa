# packages/aoa-action-machine/src/aoa/action_machine/intents/depends/__init__.py
"""Class-level ``@depends`` decorator for ``DependsIntent``."""

from aoa.action_machine.intents.depends.depends_decorator import depends
from aoa.action_machine.intents.depends.depends_eligible import DependsEligible
from aoa.action_machine.intents.depends.depends_intent import DependsIntent

__all__ = ["DependsEligible", "DependsIntent", "depends"]
