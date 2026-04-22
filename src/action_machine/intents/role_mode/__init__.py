# src/action_machine/intents/role_mode/__init__.py
"""Role lifecycle mode enum, ``@role_mode`` decorator, and ``RoleModeIntent`` mixin."""

from __future__ import annotations

# pylint: disable=undefined-all-variable
# ``__all__`` lists lazy names resolved in :func:`__getattr__` (PEP 562).
import importlib
from typing import Any

# Import only ``role_mode_intent`` here: eager loading of ``role_mode_decorator``
# would pull ``BaseRole`` while ``auth`` / ``system_role`` still need
# ``RoleMode`` from this module (circular import).
from action_machine.intents.role_mode.role_mode_intent import RoleModeIntent

_DECORATOR_MODULE = "action_machine.intents.role_mode.role_mode_decorator"
_LAZY_FROM_DECORATOR = frozenset({"RoleMode", "role_mode"})


def __getattr__(name: str) -> Any:
    if name in _LAZY_FROM_DECORATOR:
        module = importlib.import_module(_DECORATOR_MODULE)
        value = getattr(module, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(__all__)


__all__ = ["RoleMode", "RoleModeIntent", "role_mode"]
