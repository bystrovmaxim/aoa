# src/action_machine/intents/role_mode/__init__.py
"""Role lifecycle mode enum, ``@role_mode`` decorator, and ``RoleModeIntent`` mixin."""

from __future__ import annotations

from action_machine.intents.role_mode.role_mode_decorator import RoleMode, role_mode
from action_machine.intents.role_mode.role_mode_intent import RoleModeIntent

__all__ = ["RoleMode", "RoleModeIntent", "role_mode"]
