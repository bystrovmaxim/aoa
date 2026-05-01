# src/action_machine/intents/check_roles/check_roles_intent_resolver.py
"""CheckRolesIntentResolver — reads ``@check_roles`` scratch on action classes."""

from __future__ import annotations

from typing import Any

from action_machine.auth.base_role import BaseRole
from action_machine.exceptions.missing_check_roles_error import MissingCheckRolesError
from action_machine.intents.role_mode.role_mode_decorator import RoleMode


class CheckRolesIntentResolver:
    """
    AI-CORE-BEGIN
    ROLE: Surface ``_role_info`` / ``spec`` written by ``@check_roles`` and ``RoleMode`` from ``@role_mode``.
    CONTRACT: :meth:`resolve_check_roles` returns stored ``spec`` or raises :exc:`~action_machine.exceptions.MissingCheckRolesError`; :meth:`resolve_role_mode` reads ``@role_mode``.
    AI-CORE-END
    """

    @staticmethod
    def resolve_role_mode(role_cls: type[BaseRole]) -> RoleMode:
        """Return ``RoleMode`` stored by ``@role_mode`` on ``role_cls`` (``_role_mode_info``)."""
        return RoleMode.declared_for(role_cls)

    @staticmethod
    def resolve_check_roles(action_cls: type) -> Any:
        """Return `_role_info['spec']` from ``@check_roles``. Raises ``MissingCheckRolesError`` when absent."""
        try:
            return action_cls._role_info["spec"]
        except (AttributeError, KeyError, TypeError) as exc:
            raise MissingCheckRolesError(action_cls) from exc
