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
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Base model classes define stable framework contracts for action components.
- Exception exports are re-exported from ``action_machine.model.exceptions``.
- ``__all__`` is the canonical public surface of this package.

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
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- This module is an export surface; it does not contain model logic itself.
- Wildcard re-export is intentional and controlled via ``exceptions.__all__``.
- Backward compatibility depends on keeping exported names stable.

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

from action_machine.model import exceptions as _exceptions
from action_machine.model.base_action import BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from action_machine.model.base_schema import BaseSchema
from action_machine.model.base_state import BaseState
from action_machine.model.exceptions import *  # noqa: F403

__all__ = [
    "BaseAction",
    "BaseParams",
    "BaseResult",
    "BaseSchema",
    "BaseState",
    *_exceptions.__all__,
]
