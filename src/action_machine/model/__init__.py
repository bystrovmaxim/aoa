# src/action_machine/model/__init__.py
"""
ActionMachine core model public API.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

This package exports the base model contracts used by actions:
``BaseAction``, ``BaseParams``, ``BaseResult``, ``BaseSchema``, ``BaseState``,
and shared model-level exceptions.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    Action implementation
          |
          +--> BaseParams  (input contract)
          +--> BaseState   (mutable execution state)
          +--> BaseResult  (output contract)
          +--> BaseSchema  (typed schema helpers)
          |
          v
       BaseAction (ties contracts together)
          |
          v
    Runtime / adapters consume typed model interfaces

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path:
    A feature imports ``BaseAction`` and base contracts from this package and
    defines strongly typed params/state/result models for one action.

Edge case:
    A model validation or contract misuse raises an exception re-exported here
    from ``action_machine.model.exceptions``.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Public model gateway for ActionMachine contracts.
CONTRACT: Re-export base model classes and model exceptions consistently.
INVARIANTS: __all__ defines API surface; exception list comes from submodule.
FLOW: Import from model package -> consume Base* contracts -> runtime usage.
FAILURES: Contract misuse is signaled through exported model exceptions.
EXTENSION POINTS: Add new public model contract only via explicit __all__.
AI-CORE-END
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from action_machine.model import exceptions as _exceptions
from action_machine.model.base_action import BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from action_machine.model.base_schema import BaseSchema
from action_machine.model.base_state import BaseState
from action_machine.model.exceptions import *  # noqa: F403
from action_machine.model.params_node import ParamsNode
from action_machine.model.result_node import ResultNode

if TYPE_CHECKING:
    from action_machine.model.action_node import ActionNode


def __getattr__(name: str) -> Any:
    """Lazy ``ActionNode`` — avoids import cycle with :mod:`action_machine.domain.base_domain`."""
    if name == "ActionNode":
        from action_machine.model.action_node import (  # pylint: disable=import-outside-toplevel
            ActionNode as ActionNodeImpl,
        )

        return ActionNodeImpl
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "ActionNode",
    "BaseAction",
    "BaseParams",
    "BaseResult",
    "BaseSchema",
    "BaseState",
    "ParamsNode",
    "ResultNode",
    *_exceptions.__all__,
]
