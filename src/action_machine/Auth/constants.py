# src/action_machine/auth/constants.py
"""
ActionMachine authentication constants.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

This module contains special string constants used by the @check_roles decorator
and ActionProductMachine to determine the role-checking mode.

Constants are defined at module scope (not inside a class), which enables
easy import and usage:

    from action_machine.auth import ROLE_NONE, ROLE_ANY

═══════════════════════════════════════════════════════════════════════════════
CONSTANTS
═══════════════════════════════════════════════════════════════════════════════

    ROLE_NONE : str
        Marker for "authentication not required." The action is available to any
        user, including anonymous users with no roles. The machine skips role
        checks when validating this marker.

    ROLE_ANY : str
        Marker for "any role is acceptable." The action requires authentication
        and the user must have at least one role, but the specific role does not
        matter.

═══════════════════════════════════════════════════════════════════════════════
USAGE
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.auth import check_roles, ROLE_NONE, ROLE_ANY

    @check_roles(ROLE_NONE)
    class PingAction(BaseAction[BaseParams, BaseResult]):
        ...

    @check_roles(ROLE_ANY)
    class ProfileAction(BaseAction[ProfileParams, ProfileResult]):
        ...

    @check_roles("admin")
    class AdminAction(BaseAction[AdminParams, AdminResult]):
        ...

    @check_roles(["user", "manager"])
    class OrderAction(BaseAction[OrderParams, OrderResult]):
        ...

═══════════════════════════════════════════════════════════════════════════════
INTEGRATION WITH THE MACHINE
═══════════════════════════════════════════════════════════════════════════════

ActionProductMachine._check_action_roles() compares the spec from ClassMetadata
against these constants:

    if role_spec == ROLE_NONE:
        # Access without authentication is always allowed
    elif role_spec == ROLE_ANY:
        # At least one role is required
    elif isinstance(role_spec, list):
        # One of the listed roles is required
    else:
        # A specific role is required
"""

ROLE_NONE: str = "__NONE__"
"""Action does not require authentication. Available to everyone, including anonymous users."""

ROLE_ANY: str = "__ANY__"
"""Action requires authentication, but any role is acceptable."""
