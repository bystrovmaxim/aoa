# src/action_machine/core/components/role_checker.py
"""
Role checker component wrapper.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provide a component entry point for the role-check stage in the machine
orchestration. Currently delegates to existing machine internals; full logic
migration happens in a later step.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    ActionProductMachine
        │
        └── RoleChecker.check(machine, action, context, runtime)
                │
                └── machine._check_action_roles(...)   // temporary delegation

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Component receives a reference to `GateCoordinator` for future snapshot reads.
- Delegation target remains stable during scaffolding phase.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path:
- `RoleChecker.check(...)` delegates to `machine._check_action_roles(...)` and
  returns `None` when access is allowed.

Edge case:
- Delegated check raises `AuthorizationError` for missing required role.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Implementation is temporary and delegates to a private machine method.
- AuthorizationError propagation matches existing machine behavior.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Role-check component scaffolding.
CONTRACT: check(action, context, runtime) -> None or AuthorizationError.
INVARIANTS: GateCoordinator injected; role semantics must match machine contract.
FLOW: runtime.role_spec + context.user.roles -> allow or AuthorizationError.
FAILURES: AuthorizationError raised on role mismatch.
EXTENSION POINTS: custom role strategies can replace this component.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from action_machine.context.context import Context
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.core.exceptions import AuthorizationError
from action_machine.metadata.gate_coordinator import GateCoordinator
from action_machine.auth.constants import ROLE_ANY, ROLE_NONE


class RoleChecker:
    """Component entry point for role-check stage.

    This is a scaffolding implementation that delegates to the existing
    machine's internal method. Full migration of role-checking logic will
    happen in a subsequent step.
    """

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