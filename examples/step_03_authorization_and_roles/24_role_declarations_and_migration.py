"""Role declarations accept role choices and reject removed conditions.
Run: .venv/bin/python examples/step_03_authorization_and_roles/24_role_declarations_and_migration.py
"""

from __future__ import annotations

from pydantic import ValidationError

from aoa.action_machine.auth import ApplicationRole, GuestRole
from aoa.action_machine.exceptions import RoleSpecTypeError
from aoa.action_machine.intents.access_control import Gate, Refused
from aoa.action_machine.intents.check_roles import check_roles

# %% Setup


class ManagerRole(ApplicationRole):
    """Permit order management."""

    name = "manager"
    description = "Manage orders"


class AuditorRole(ApplicationRole):
    """Permit independent reviews."""

    name = "auditor"
    description = "Review orders"


# %% Run


def main() -> None:
    """Compare legal declarations with migration failures."""
    check_roles(ManagerRole)
    check_roles(ManagerRole, AuditorRole)
    check_roles((ManagerRole, AuditorRole))
    check_roles([ManagerRole, AuditorRole])
    check_roles(ManagerRole, ManagerRole)
    check_roles(GuestRole, ManagerRole)
    print("accepted: one role, positional roles, tuple, list, duplicates, guest alternative")

    for keyword in ("guard", "guard_reason", "when"):
        try:
            check_roles(ManagerRole, **{keyword: "old condition"})
        except RoleSpecTypeError as exc:
            expected = (
                f"@check_roles declares roles only; {keyword!r} belonged to the removed condition layer. "
                "Move the condition into the operation's @access_decide method and return "
                'Refused("REASON") or FORBIDDEN_OBJECT for the branch that used to refuse.'
            )
            assert str(exc) == expected
            print(type(exc).__name__ + ":", str(exc))
        else:
            raise AssertionError(f"The removed keyword {keyword} must be refused.")

    try:
        from aoa.action_machine.intents.check_roles import grant  # noqa: F401
    except ImportError as exc:
        assert "cannot import name 'grant'" in str(exc)
        print(type(exc).__name__ + ":", str(exc))
    else:
        raise AssertionError("The removed grant import must fail.")
    try:
        from aoa.action_machine.intents.check_roles import Grant  # noqa: F401
    except ImportError as exc:
        assert "cannot import name 'Grant'" in str(exc)
        print(type(exc).__name__ + ":", str(exc))
    else:
        raise AssertionError("The removed Grant import must fail.")

    import aoa.action_machine.exceptions as exceptions

    assert not hasattr(exceptions, "AccessConditionAsyncError")
    assert not hasattr(exceptions, "ConditionReasonError")

    assert [gate.value for gate in Gate] == ["AUTH_COORDINATOR", "CHECK_ROLES", "ACCESS_DECIDE"]
    print("gates:", [gate.value for gate in Gate])
    for word in ("WHEN", "GUARD"):
        try:
            getattr(Gate, word)
        except AttributeError as exc:
            assert str(exc) == f"type object 'Gate' has no attribute {word!r}"
            print(type(exc).__name__ + ":", str(exc))
        else:
            raise AssertionError("Removed gate members must be absent.")
        try:
            Gate(word)
        except ValueError as exc:
            assert str(exc) == f"{word!r} is not a valid Gate"
            print(type(exc).__name__ + ":", str(exc))
        else:
            raise AssertionError("Removed gate words must fail enum conversion.")
        try:
            Refused.model_validate({"gate": word})
        except ValidationError as exc:
            error = exc.errors(include_url=False)[0]
            assert error["loc"] == ("gate",) and error["type"] == "enum"
            assert error["msg"] == "Input should be 'AUTH_COORDINATOR', 'CHECK_ROLES' or 'ACCESS_DECIDE'"
            print(type(exc).__name__ + ":", str(exc))
        else:
            raise AssertionError("Removed gate words must fail payload validation.")
    assert Refused().gate is Gate.ACCESS_DECIDE
    print("default refusal:", Refused().model_dump(mode="json"))


if __name__ == "__main__":
    main()
