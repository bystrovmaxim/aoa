# packages/aoa-action-machine/src/aoa/action_machine/intents/check_roles/check_roles_intent_resolver.py
"""CheckRolesIntentResolver — reads ``@check_roles`` scratch on action classes."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, cast

from aoa.action_machine.auth.base_role import BaseRole
from aoa.action_machine.exceptions.missing_check_roles_error import MissingCheckRolesError
from aoa.action_machine.intents.check_roles.check_roles_intent import CheckRolesIntent
from aoa.action_machine.intents.check_roles.grant import Grant
from aoa.action_machine.intents.role_mode.role_mode_decorator import RoleMode

if TYPE_CHECKING:
    # Deferred: access_control transitively imports nearly the whole package (via
    # model.base_schema); this module sits deep inside that same transitive chain
    # (reachable from base_action.py through auth/graph), so a top-level import
    # would cycle depending on which module happens to be imported first. Only
    # ever used as a type annotation / cast target below, never constructed here.
    from aoa.action_machine.intents.access_control import FailSecurityVerdict


class CheckRolesIntentResolver:
    """
    AI-CORE-BEGIN
    ROLE: Surface ``_role_info`` / ``spec`` / ``grants`` / ``guard`` written by ``@check_roles`` and ``RoleMode`` from ``@role_mode``.
    CONTRACT: :meth:`resolve_check_roles`, :meth:`resolve_grants`, :meth:`resolve_guard`, :meth:`resolve_guard_reason` return the stored ``_role_info`` entry or raise :exc:`~aoa.action_machine.exceptions.MissingCheckRolesError`; :meth:`resolve_role_mode` reads ``@role_mode``.
    AI-CORE-END
    """

    @staticmethod
    def resolve_role_mode(role_cls: type[BaseRole]) -> RoleMode:
        """Return ``RoleMode`` stored by ``@role_mode`` on ``role_cls`` (``_role_mode_info``)."""
        return RoleMode.declared_for(role_cls)

    @staticmethod
    def resolve_check_roles(action_cls: type[CheckRolesIntent]) -> Any:
        """Return `_role_info['spec']` from ``@check_roles``. Raises ``MissingCheckRolesError`` when absent."""
        try:
            return action_cls._role_info["spec"]
        except (AttributeError, KeyError, TypeError) as exc:
            raise MissingCheckRolesError(action_cls) from exc

    @staticmethod
    def resolve_grants(action_cls: type[CheckRolesIntent]) -> list[Grant]:
        """Return `_role_info['grants']` from ``@check_roles``. Raises ``MissingCheckRolesError`` when absent."""
        try:
            return cast("list[Grant]", action_cls._role_info["grants"])
        except (AttributeError, KeyError, TypeError) as exc:
            raise MissingCheckRolesError(action_cls) from exc

    @staticmethod
    def resolve_guard(action_cls: type[CheckRolesIntent]) -> Callable[..., bool] | None:
        """Return `_role_info['guard']` from ``@check_roles``. Raises ``MissingCheckRolesError`` when absent."""
        try:
            return cast("Callable[..., bool] | None", action_cls._role_info["guard"])
        except (AttributeError, KeyError, TypeError) as exc:
            raise MissingCheckRolesError(action_cls) from exc

    @staticmethod
    def resolve_guard_reason(action_cls: type[CheckRolesIntent]) -> FailSecurityVerdict | None:
        """Return `_role_info['guard_reason']` — ``guard=``'s companion, or ``None`` when there is no ``guard=``."""
        try:
            return cast("FailSecurityVerdict | None", action_cls._role_info["guard_reason"])
        except (AttributeError, KeyError, TypeError) as exc:
            raise MissingCheckRolesError(action_cls) from exc
