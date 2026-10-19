"""A role's mode is declared once, and a wrong one is refused where it is written."""

from __future__ import annotations

from aoa.action_machine.auth import ApplicationRole
from aoa.action_machine.exceptions import RoleSpecTypeError
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.role_mode import RoleMode, role_mode

# %% A member of the enum, and nothing else


@role_mode(RoleMode.ALIVE)
class ViewerRole(ApplicationRole):
    """Read the catalog."""

    name = "viewer"
    description = "Can read the catalog"


print("declared:", ViewerRole._role_mode_info)

# %% The string the enum carries is not the member


try:

    @role_mode("alive")
    class MistypedRole(ApplicationRole):
        """Written the way the value looks."""

        name = "mistyped"
        description = "Carries a string instead of a member"

except Exception as error:  # the declaration fails; the class name is never bound
    print(type(error).__name__ + ":", error)

# %% The parentheses are part of the call


try:

    @role_mode
    class ParenthesislessRole(ApplicationRole):
        """Forgot the call."""

        name = "parenthesisless"
        description = "Decorated without parentheses"

except Exception as error:
    print(type(error).__name__ + ":", error)

# %% A member decides nothing by itself; the consumers do


@role_mode(RoleMode.UNUSED)
class RetiredRole(ApplicationRole):
    """Kept in the code, never required."""

    name = "retired"
    description = "Kept, unused"


print("declared:", RetiredRole._role_mode_info)


try:

    @check_roles(RetiredRole)
    class WithdrawAction:
        """Would have required a role that is not used."""

except RoleSpecTypeError as error:
    print(type(error).__name__ + ":", error)
