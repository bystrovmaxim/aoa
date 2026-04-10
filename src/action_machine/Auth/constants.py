# src/action_machine/auth/constants.py
"""
ActionMachine authentication constants.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provide special string constants used by the ``@check_roles`` decorator and
``ActionProductMachine`` to determine the role-checking mode.

═══════════════════════════════════════════════════════════════════════════════
CONSTANTS
═══════════════════════════════════════════════════════════════════════════════

- ``ROLE_NONE`` — authentication not required; action is available to everyone,
  including anonymous users.
- ``ROLE_ANY``  — authentication required, but any role is acceptable; the user
  must have at least one role.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.auth import check_roles, ROLE_NONE, ROLE_ANY

    @check_roles(ROLE_NONE)
    class PingAction(BaseAction[BaseParams, BaseResult]):
        ...

    @check_roles(ROLE_ANY)
    class ProfileAction(BaseAction[ProfileParams, ProfileResult]):
        ...

═══════════════════════════════════════════════════════════════════════════════
INTEGRATION
═══════════════════════════════════════════════════════════════════════════════

``ActionProductMachine._check_action_roles()`` compares the role spec from the
snapshot against these constants to decide whether to allow or deny execution.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Authentication constants module.
CONTRACT: Export ROLE_NONE and ROLE_ANY as immutable string markers.
INVARIANTS: Constants are read‑only; their values are fixed.
FLOW: Imported by decorators and machine; used in runtime role checks.
FAILURES: None (pure constants).
EXTENSION POINTS: New special markers can be added following the same pattern.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

ROLE_NONE: str = "__NONE__"
"""Action does not require authentication. Available to everyone, including anonymous users."""

ROLE_ANY: str = "__ANY__"
"""Action requires authentication, but any role is acceptable."""
