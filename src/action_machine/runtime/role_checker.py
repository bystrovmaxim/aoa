# src/action_machine/runtime/role_checker.py
"""
Runtime enforcement of ``@check_roles`` against ``Context.user.roles``.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``RoleChecker.check`` is the machine gate that compares declared role requirements
(materialized as ``@check_roles`` association edges on
:class:`~action_machine.graph_model.nodes.action_graph_node.ActionGraphNode`) to
the authenticated user's role types. Matching uses ``issubclass(user_role, required)``.
``RoleMode.SILENCED`` user roles are ignored entirely.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    action_node.roles (``RoleGraphEdge`` → wired :class:`~action_machine.graph_model.nodes.role_graph_node.RoleGraphNode`)
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

from typing import Any

from action_machine.auth.any_role import AnyRole
from action_machine.auth.base_role import BaseRole
from action_machine.auth.none_role import NoneRole
from action_machine.context.context import Context
from action_machine.exceptions.authorization_error import AuthorizationError
from action_machine.graph_model.nodes.action_graph_node import ActionGraphNode
from action_machine.graph_model.nodes.role_graph_node import RoleGraphNode
from action_machine.intents.role_mode.role_mode_decorator import RoleMode
from action_machine.model.base_action import BaseAction


class RoleChecker:
    """Enforces ``@check_roles`` using ``ActionGraphNode`` role edges and user role types."""

    @classmethod
    def _check_roles_spec_from_action_edges(
        cls,
        action_node: ActionGraphNode[BaseAction[Any, Any]],
    ) -> Any:
        """
        Reconstruct the ``@check_roles`` spec shape from wired role association edges.

        Returns ``NoneRole``, ``AnyRole``, a single concrete ``BaseRole`` subtype, or
        a tuple of subtypes (OR semantics), matching :class:`RoleGraphEdge` emission order.
        """

        parts: list[type[BaseRole]] = []
        for edge in action_node.roles:
            target = edge.target_node
            if not isinstance(target, RoleGraphNode):
                raise TypeError(
                    f"Role association edge on action {action_node.node_id!r} must resolve to a "
                    f"Role interchange row; got {type(target).__name__!r}. "
                    "Ensure the graph coordinator wired ``RoleGraphEdge.target_node``.",
                )
            rc = target.node_obj
            if not isinstance(rc, type) or not issubclass(rc, BaseRole):
                raise TypeError(
                    f"Role graph node on {action_node.node_id!r} has invalid node_obj {rc!r}; "
                    "expected a BaseRole subclass.",
                )
            parts.append(rc)

        if len(parts) == 1:
            return parts[0]
        return tuple(parts)

    def check(
        self,
        context: Context,
        action_node: ActionGraphNode[BaseAction[Any, Any]],
    ) -> None:
        """Validate role access; raise ``AuthorizationError`` or ``TypeError`` on failure."""
        if not action_node.roles:
            raise TypeError(
                f"Action {action_node.node_id} does not have a @check_roles "
                f"decorator. Specify @check_roles(NoneRole) explicitly if "
                f"the action is accessible without authentication."
            )
        role_spec = self._check_roles_spec_from_action_edges(action_node)
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
            f"Invalid reconstructed @check_roles spec: {role_spec!r} "
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
