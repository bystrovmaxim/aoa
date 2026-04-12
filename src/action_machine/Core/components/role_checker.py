# src/action_machine/core/components/role_checker.py
"""
Runtime enforcement of ``@check_roles`` against ``Context.user.roles``.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``RoleChecker.check`` is the machine gate that compares the coordinator snapshot
``role_spec`` (``ROLE_NONE``, ``ROLE_ANY``, one ``BaseRole`` type, or a tuple of
types with OR semantics) to the authenticated user's role tokens. Matching uses
**inheritance (MRO)**, **transitive ``includes``**, and stable ``name`` strings
resolved through ``resolve_role_name_to_type``. ``RoleMode.SILENCED`` user roles
are ignored entirely.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    runtime.role_spec  +  Context.user.roles (str tokens)
              │
              ├── ROLE_NONE → allow
              ├── ROLE_ANY  → require ≥1 non‑SILENCED token
              │
              └── type | tuple[type, …]
                        │
                        ▼
              resolve_role_name_to_type(token)
                        │
                        ▼
              get_declared_role_mode → skip if SILENCED
                        │
                        ▼
              required ∈ expand_role_privileges(resolved_type) ?

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- ``runtime.role_spec`` must match the coordinator ``role`` facet contract.
- Missing ``@check_roles`` on the action class → ``TypeError`` (same as before).
- ``RoleMode.UNUSED`` / ``DEPRECATED`` on **required** roles are enforced in
  ``@check_roles`` (``ValueError`` / ``DeprecationWarning``), not here.
- Privilege expansion is memoized per role type via ``expand_role_privileges``.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path: user token ``\"order_manager\"`` resolves to ``OrderManagerRole``;
``@check_roles(OrderViewerRole)`` passes because ``includes`` grants viewer.

Edge case: only ``RoleMode.SILENCED`` tokens → ``ROLE_ANY`` fails with
``AuthorizationError``.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- ``UserInfo.roles`` is modeled as ``list[str]``; non-string entries are ignored
  until the schema is extended.
- Cyclic ``includes`` graphs are tolerated at runtime (visited-set) if the graph
  was built before validation tightened; a normal ``build()`` rejects cycles.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Machine pipeline role gate.
CONTRACT: check(action, context, runtime) → None; deny → AuthorizationError.
INVARIANTS: SILENCED filtered; expansion = MRO ∪ transitive includes.
FLOW: After snapshot cache read; before aspect pipeline body execution.
FAILURES: AuthorizationError, TypeError (missing spec / invalid snapshot).
EXTENSION POINTS: Custom ``RoleChecker`` injection on ``ActionProductMachine``.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from typing import Any, Protocol

from action_machine.auth.base_role import BaseRole
from action_machine.auth.constants import ROLE_ANY, ROLE_NONE
from action_machine.auth.role_expansion import (
    expand_role_privileges,
    resolve_role_name_to_type,
)
from action_machine.auth.role_mode import RoleMode, get_declared_role_mode
from action_machine.context.context import Context
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.core.exceptions import AuthorizationError
from action_machine.metadata.gate_coordinator import GateCoordinator


class RoleChecker:
    """Enforces ``@check_roles`` using coordinator ``role_spec`` and user role tokens."""

    def __init__(self, coordinator: GateCoordinator) -> None:
        self._coordinator = coordinator

    def check(
        self,
        action: BaseAction[BaseParams, BaseResult],
        context: Context,
        runtime: _RoleRuntime,
    ) -> None:
        """Validate role access; raise ``AuthorizationError`` or ``TypeError`` on failure."""
        _ = self._coordinator
        role_spec = runtime.role_spec
        if role_spec is None:
            raise TypeError(
                f"Action {action.__class__.__name__} does not have a @check_roles "
                f"decorator. Specify @check_roles(ROLE_NONE) explicitly if "
                f"the action is accessible without authentication."
            )
        raw_roles = context.user.roles

        if role_spec == ROLE_NONE:
            return
        if role_spec == ROLE_ANY:
            active = _active_user_role_strings(raw_roles)
            if not active:
                raise AuthorizationError(
                    "Authentication required: user must have at least one role"
                )
            return

        active = _active_user_role_strings(raw_roles)

        if isinstance(role_spec, tuple):
            if any(
                _user_string_grants_requirement(ur, req)
                for ur in active
                for req in role_spec
            ):
                return
            names = [r.name for r in role_spec]
            raise AuthorizationError(
                f"Access denied. Required one of the roles: {names}, "
                f"user roles: {raw_roles}"
            )
        if isinstance(role_spec, type) and issubclass(role_spec, BaseRole):
            if any(_user_string_grants_requirement(ur, role_spec) for ur in active):
                return
            raise AuthorizationError(
                f"Access denied. Required role: '{role_spec.name}', "
                f"user roles: {raw_roles}"
            )
        raise TypeError(
            f"Invalid role_spec in runtime snapshot: {role_spec!r} "
            f"({type(role_spec).__name__})."
        )


def _active_user_role_strings(user_roles: list[Any]) -> list[str]:
    """Drop tokens that resolve to a ``RoleMode.SILENCED`` class."""
    out: list[str] = []
    for t in user_roles:
        if not isinstance(t, str):
            continue
        rt = resolve_role_name_to_type(t)
        if get_declared_role_mode(rt) is RoleMode.SILENCED:
            continue
        out.append(t)
    return out


def _user_string_grants_requirement(user_role: str, required: type[BaseRole]) -> bool:
    resolved = resolve_role_name_to_type(user_role)
    if get_declared_role_mode(resolved) is RoleMode.SILENCED:
        return False
    return required in expand_role_privileges(resolved)


class _RoleRuntime(Protocol):
    @property
    def role_spec(self) -> Any: ...
