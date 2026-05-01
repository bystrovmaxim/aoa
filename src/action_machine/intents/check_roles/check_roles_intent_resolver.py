# src/action_machine/intents/check_roles/check_roles_intent_resolver.py
"""CheckRolesIntentResolver — reads ``@check_roles`` scratch on action classes."""

from __future__ import annotations

from typing import Any

from action_machine.auth.base_role import BaseRole
from action_machine.intents.role_mode.role_mode_decorator import RoleMode


class CheckRolesIntentResolver:
    """
    AI-CORE-BEGIN
    ROLE: Surface ``_role_info`` / ``spec`` written by ``@check_roles`` and ``RoleMode`` from ``@role_mode``.
    CONTRACT: ``resolve_required_role_types`` returns stored ``spec`` or ``None`` when ``_role_info`` is missing; :meth:`resolve_role_mode` reads ``@role_mode``.
    AI-CORE-END
    """

    @staticmethod
    def resolve_role_mode(role_cls: type[BaseRole]) -> RoleMode:
        """Return ``RoleMode`` stored by ``@role_mode`` on ``role_cls`` (``_role_mode_info``)."""
        return RoleMode.declared_for(role_cls)

    @staticmethod
    def resolve_required_role_types(action_cls: type) -> Any:
        """Return `_role_info['spec']`, or ``None`` if ``@check_roles`` did not set storage."""
        try:
            return action_cls._role_info["spec"]
        except (AttributeError, KeyError, TypeError):
            return None
