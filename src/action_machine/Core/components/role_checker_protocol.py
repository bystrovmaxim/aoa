# src/action_machine/core/components/role_checker_protocol.py
"""
Protocol for role checking component.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Define the contract for validating user roles against action role requirements.
Implementations are expected to raise `AuthorizationError` when access is denied.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    ActionProductMachine
        │
        └── RoleCheckerProtocol.check(machine, action, context, runtime)
                │
                ├── reads role spec from runtime.role_spec (or fallback)
                ├── compares against context.user.roles
                └── returns None or raises AuthorizationError

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Implementations must raise `AuthorizationError` when the user lacks required roles.
- Special markers `ROLE_NONE` and `ROLE_ANY` must be handled according to the
  framework's semantics.
- The protocol does not dictate how the role spec is obtained; it relies on the
  provided `runtime` snapshot or equivalent source.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path:
- Implementation allows access when user roles satisfy role spec.

Edge case:
- Implementation raises `AuthorizationError` for denied access.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Protocol does not enforce specific validation order; only the outcome contract.
- Implementations should not modify the `runtime` or `context`.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Role checker contract.
CONTRACT: check(action, context, runtime) -> None or AuthorizationError.
INVARIANTS: raises AuthorizationError on access denial; handles ROLE_NONE/ROLE_ANY.
FLOW: input context + runtime -> role validation -> None or error.
FAILURES: AuthorizationError when role requirements are not met.
EXTENSION POINTS: custom role-checking logic can be injected via implementation.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from typing import Any, Protocol

from action_machine.context.context import Context
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult


class RoleCheckerProtocol(Protocol):
    """Contract for role validation step in machine orchestration."""

    def check(
        self,
        action: BaseAction[BaseParams, BaseResult],
        context: Context,
        runtime: Any,
    ) -> None:
        """
        Validate role access for an action execution.

        Args:
            action: Action instance being executed.
            context: Execution context containing user roles.
            runtime: Pre‑computed action execution cache.

        Raises:
            AuthorizationError: If role requirements are not satisfied.
        """
        pass
