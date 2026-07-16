# packages/aoa-action-machine/src/aoa/action_machine/runtime/role_checker.py
"""
Runtime enforcement of ``@check_roles`` against ``Context.user.roles``.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``RoleChecker.check`` is the machine gate that compares declared role requirements
(materialized as ``@check_roles`` association edges on
:class:`~aoa.action_machine.graph.nodes.action_graph_node.ActionGraphNode`) to
the authenticated user's role types. Matching uses ``issubclass(user_role, required)``.
``RoleMode.SILENCED`` user roles are ignored entirely.

After a role matches, its grant's ``when=`` condition (``edge.properties["when"]``,
see :mod:`~aoa.action_machine.intents.check_roles.check_roles_decorator`) is
evaluated against ``context.user``. Grants are tried in declaration order, ``any()``
semantics: the first grant whose role matches *and* whose ``when=`` (if any) returns
``True`` wins — a grant whose role matches but whose ``when=`` returns ``False`` is
skipped, not fatal, so a later grant can still win. Once a grant wins, the action's
shared ``guard=`` (``action_node.properties["guard"]``) is evaluated once against
``context.user`` and ``params``. ``AuthorizationError.level`` records which gate
rejected the request: ``1`` — no role matched at all; ``2`` — a role matched but its
``when=`` or the ``guard=`` rejected the request.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    action_node.roles (``RoleGraphEdge`` → wired :class:`~aoa.action_machine.graph.nodes.role_graph_node.RoleGraphNode`)
              │
              ├── GuestRole → allow (subject to guard=)
              ├── AnyRole  → require ≥1 non‑SILENCED role type (subject to guard=)
              │
              └── type | tuple[type, …]
                        │
                        ▼
              RoleMode.declared_for → skip if SILENCED
                        │
                        ▼
              issubclass(user_role, required) ?  (level 1 if none match)
                        │
                        ▼
              edge.properties["when"](context.user) ?  (per matched grant, any(); level 2 if all reject)
                        │
                        ▼
              action_node.properties["guard"](context.user, params) ?  (once, shared; level 2 if it rejects)

"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from aoa.action_machine.auth.any_role import AnyRole
from aoa.action_machine.auth.base_role import BaseRole
from aoa.action_machine.auth.guest_role import GuestRole
from aoa.action_machine.context.context import Context
from aoa.action_machine.exceptions.authorization_error import AuthorizationError
from aoa.action_machine.graph.edges.role_graph_edge import RoleGraphEdge
from aoa.action_machine.graph.nodes.action_graph_node import ActionGraphNode
from aoa.action_machine.graph.nodes.role_graph_node import RoleGraphNode
from aoa.action_machine.intents.role_mode.role_mode_decorator import RoleMode
from aoa.action_machine.model.base_action import BaseAction


class RoleChecker:
    """Enforces ``@check_roles`` using ``ActionGraphNode`` role edges and user role types."""

    @classmethod
    def _role_cls_for_edge(
        cls,
        action_node: ActionGraphNode[BaseAction[Any, Any]],
        edge: RoleGraphEdge,
    ) -> type[BaseRole]:
        """Extract and validate the wired role class for one ``@check_roles`` edge."""
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
        return rc

    @classmethod
    def _check_roles_spec_from_action_edges(
        cls,
        action_node: ActionGraphNode[BaseAction[Any, Any]],
    ) -> Any:
        """
        Reconstruct the ``@check_roles`` spec shape from wired role association edges.

        Returns ``GuestRole``, ``AnyRole``, a single concrete ``BaseRole`` subtype, or
        a tuple of subtypes (OR semantics), matching :class:`RoleGraphEdge` emission order.
        """
        parts = [cls._role_cls_for_edge(action_node, edge) for edge in action_node.roles]
        if len(parts) == 1:
            return parts[0]
        return tuple(parts)

    def check(
        self,
        context: Context,
        action_node: ActionGraphNode[BaseAction[Any, Any]],
        params: Any = None,
    ) -> None:
        """Validate role access, per-grant ``when=``, and ``guard=``.

        Raises ``AuthorizationError`` (``level`` 1 or 2) or ``TypeError`` on failure.
        """
        if not action_node.roles:
            raise TypeError(
                f"Action {action_node.node_id} does not have a @check_roles "
                f"decorator. Specify @check_roles(GuestRole) explicitly if "
                f"the action is accessible without authentication."
            )
        role_spec = self._check_roles_spec_from_action_edges(action_node)
        raw_roles = context.user.roles
        guard = action_node.properties.get("guard")

        if role_spec is GuestRole:
            # Exactly one edge: `_check_roles_spec_from_action_edges` only returns a bare
            # sentinel (not a tuple) when there is a single grant. `grant(GuestRole, when=...)`
            # is a valid declaration (GuestRole is an ordinary BaseRole subclass as far as
            # `grant()` is concerned) and must not be silently ignored.
            when = action_node.roles[0].properties.get("when")
            if when is not None and not when(context.user):
                raise AuthorizationError("Access denied. GuestRole grant's when= condition was not met.", level=2)
            _enforce_guard(context.user, params, guard)
            return
        if role_spec is AnyRole:
            active = _active_user_roles(raw_roles)
            if not active:
                raise AuthorizationError("Authentication required: user must have at least one role", level=1)
            when = action_node.roles[0].properties.get("when")
            if when is not None and not when(context.user):
                raise AuthorizationError("Access denied. AnyRole grant's when= condition was not met.", level=2)
            _enforce_guard(context.user, params, guard)
            return

        active = _active_user_roles(raw_roles)

        if isinstance(role_spec, tuple) or (isinstance(role_spec, type) and issubclass(role_spec, BaseRole)):
            role_matched = False
            for edge in action_node.roles:
                role_cls = self._role_cls_for_edge(action_node, edge)
                if not any(_user_role_grants_requirement(ur, role_cls) for ur in active):
                    continue
                role_matched = True
                when = edge.properties.get("when")
                if when is not None and not when(context.user):
                    continue
                _enforce_guard(context.user, params, guard)
                return

            user_names = [r.name for r in raw_roles]
            if isinstance(role_spec, tuple):
                names = [r.name for r in role_spec]
                if role_matched:
                    raise AuthorizationError(
                        f"Access denied. Required one of the roles: {names}, matched but a "
                        f"condition rejected the request; user roles: {user_names}",
                        level=2,
                    )
                raise AuthorizationError(
                    f"Access denied. Required one of the roles: {names}, " f"user roles: {user_names}",
                    level=1,
                )
            if role_matched:
                raise AuthorizationError(
                    f"Access denied. Required role: '{role_spec.name}', matched but a "
                    f"condition rejected the request; user roles: {user_names}",
                    level=2,
                )
            raise AuthorizationError(
                f"Access denied. Required role: '{role_spec.name}', " f"user roles: {user_names}",
                level=1,
            )
        raise TypeError(f"Invalid reconstructed @check_roles spec: {role_spec!r} " f"({type(role_spec).__name__}).")


def _enforce_guard(user: Any, params: Any, guard: Callable[..., bool] | None) -> None:
    """Raise ``AuthorizationError(level=2)`` if ``guard`` is set and returns falsy."""
    if guard is not None and not guard(user, params):
        raise AuthorizationError("Access denied. guard= condition was not met.", level=2)


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


def _user_role_grants_requirement(user_role: type[BaseRole], required: type[BaseRole]) -> bool:
    if RoleMode.declared_for(user_role) is RoleMode.SILENCED:
        return False
    return issubclass(user_role, required)
