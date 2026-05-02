# src/action_machine/runtime/role_checker.py
"""
Runtime enforcement of ``@check_roles`` against ``Context.user.roles``.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``RoleChecker.check`` is the machine gate that compares the coordinator snapshot
``role_spec`` (``NoneRole``, ``AnyRole``, one ``BaseRole`` type, or a tuple of
types with OR semantics) to the authenticated user's role types. Matching uses
``issubclass(user_role, required)``. ``RoleMode.SILENCED`` user roles are ignored
entirely.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    runtime.role_spec  +  Context.user.roles (BaseRole subclasses)
              │
              ├── NoneRole → allow
              ├── AnyRole  → require ≥1 non‑SILENCED role type
              │
              └── type | tuple[type, …]
                        │
                        ▼
              RoleMode.declared_for → skip if SILENCED
                        │
                        ▼
              issubclass(user_role, required) ?

"""

from __future__ import annotations

from typing import Any, Protocol

from action_machine.auth.any_role import AnyRole
from action_machine.auth.base_role import BaseRole
from action_machine.auth.none_role import NoneRole
from action_machine.context.context import Context
from action_machine.exceptions import AuthorizationError
from action_machine.graph_model.nodes.action_graph_node import ActionGraphNode
from action_machine.intents.role_mode.role_mode_decorator import RoleMode
from action_machine.model.base_action import BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from graph.graph_coordinator import GraphCoordinator


class RoleChecker:
    """Enforces ``@check_roles`` using coordinator ``role_spec`` and user role types."""

    def __init__(self, coordinator: GraphCoordinator) -> None:
        self._coordinator = coordinator

    def check(
        self,
        action: BaseAction[BaseParams, BaseResult],
        context: Context,
        runtime: _RoleRuntime,
        action_node: ActionGraphNode,
    ) -> None:
        """Validate role access; raise ``AuthorizationError`` or ``TypeError`` on failure."""
        _ = self._coordinator
        role_spec = runtime.role_spec
        if not action_node.roles:
            raise TypeError(
                f"Action {action_node.node_id} does not have a @check_roles "
                f"decorator. Specify @check_roles(NoneRole) explicitly if "
                f"the action is accessible without authentication."
            )
        raw_roles = context.user.roles

        if role_spec is NoneRole:
            return
        if role_spec is AnyRole:
            active = _active_user_roles(raw_roles)
            if not active:
                raise AuthorizationError(
                    "Authentication required: user must have at least one role"
                )
            return

        active = _active_user_roles(raw_roles)

        if isinstance(role_spec, tuple):
            if any(
                _user_role_grants_requirement(ur, req)
                for ur in active
                for req in role_spec
            ):
                return
            names = [r.name for r in role_spec]
            user_names = [r.name for r in raw_roles]
            raise AuthorizationError(
                f"Access denied. Required one of the roles: {names}, "
                f"user roles: {user_names}"
            )
        if isinstance(role_spec, type) and issubclass(role_spec, BaseRole):
            if any(_user_role_grants_requirement(ur, role_spec) for ur in active):
                return
            user_names = [r.name for r in raw_roles]
            raise AuthorizationError(
                f"Access denied. Required role: '{role_spec.name}', "
                f"user roles: {user_names}"
            )
        raise TypeError(
            f"Invalid role_spec in runtime snapshot: {role_spec!r} "
            f"({type(role_spec).__name__})."
        )


def _active_user_roles(
    user_roles: tuple[type[BaseRole], ...],
) -> list[type[BaseRole]]:
    """Drop role types that are ``RoleMode.SILENCED``."""
    out: list[type[BaseRole]] = []
    for rt in user_roles:
        if RoleMode.declared_for(rt) is RoleMode.SILENCED:
            continue
        out.append(rt)
    return out


def _user_role_grants_requirement(
    user_role: type[BaseRole], required: type[BaseRole]
) -> bool:
    if RoleMode.declared_for(user_role) is RoleMode.SILENCED:
        return False
    return issubclass(user_role, required)


class _RoleRuntime(Protocol):
    @property
    def role_spec(self) -> Any: ...

    @property
    def action_node(self) -> Any: ...
