# src/action_machine/core/components/role_checker.py
"""
Role checker component wrapper.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provide the role-check stage for machine orchestration. Implementation owns
``@check_roles`` semantics against ``runtime.role_spec`` and ``Context.user.roles``.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    ActionProductMachine._run_internal
        │
        └── RoleChecker.check(action, context, runtime)
                │
                └── role_spec + user.roles → allow or AuthorizationError

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- ``runtime.role_spec`` must come from the same coordinator facet contract as the machine.
- Missing ``@check_roles`` surfaces as ``TypeError`` (explicit ``ROLE_NONE`` required).

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path:
- ``check(...)`` returns ``None`` when the user satisfies the role spec.

Edge case:
- ``ROLE_ANY`` with empty ``user.roles`` raises ``AuthorizationError``.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Does not consult ``ActionProductMachine`` private helpers; logic is local to this class.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Role-check component.
CONTRACT: check(action, context, runtime) -> None; raises on deny.
INVARIANTS: spec from runtime; same semantics as machine pipeline gate.
FLOW: role_spec + user.roles -> allow or AuthorizationError / TypeError.
FAILURES: AuthorizationError, TypeError when spec missing.
EXTENSION POINTS: inject custom ``RoleChecker`` via machine constructor.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from action_machine.auth.constants import ROLE_ANY, ROLE_NONE
from action_machine.context.context import Context
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.core.exceptions import AuthorizationError
from action_machine.metadata.gate_coordinator import GateCoordinator


class RoleChecker:
    """Enforces ``@check_roles`` for one run using the machine execution runtime snapshot."""

    def __init__(self, coordinator: GateCoordinator) -> None:
        self._coordinator = coordinator

    def check(
        self,
        action: BaseAction[BaseParams, BaseResult],
        context: Context,
        runtime,
    ) -> None:
        """Validate action role access from runtime role spec."""
        _ = self._coordinator
        role_spec = runtime.role_spec
        if role_spec is None:
            raise TypeError(
                f"Action {action.__class__.__name__} does not have a @check_roles "
                f"decorator. Specify @check_roles(ROLE_NONE) explicitly if "
                f"the action is accessible without authentication."
            )
        user_roles = context.user.roles

        if role_spec == ROLE_NONE:
            return
        if role_spec == ROLE_ANY:
            if not user_roles:
                raise AuthorizationError(
                    "Authentication required: user must have at least one role"
                )
            return
        if isinstance(role_spec, list):
            if any(role in user_roles for role in role_spec):
                return
            raise AuthorizationError(
                f"Access denied. Required one of the roles: {role_spec}, "
                f"user roles: {user_roles}"
            )
        if role_spec in user_roles:
            return
        raise AuthorizationError(
            f"Access denied. Required role: '{role_spec}', user roles: {user_roles}"
        )
