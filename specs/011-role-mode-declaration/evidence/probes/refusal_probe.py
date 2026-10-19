# specs/011-role-mode-declaration/evidence/probes/refusal_probe.py
"""
Probe: the three refusals the plan fixes, worded as the decorator will word them.

This is not the implementation — it is a runnable sketch of the messages, so the
contracts and the changelog can quote what a developer will actually read.
"""

from __future__ import annotations

from collections.abc import Callable
from enum import Enum
from typing import Any, TypeVar, cast

from aoa.action_machine.exceptions.role_mode_declaration_error import RoleModeDeclarationError
from aoa.action_machine.intents.role_mode import RoleMode

_RT = TypeVar("_RT", bound=type)
_ALLOWED = ", ".join(member.name for member in RoleMode)


def proposed_role_mode(mode: RoleMode) -> Callable[[_RT], _RT]:
    """Refuse a mode that is not a member, and the class that forgot the parentheses."""
    if isinstance(mode, type):
        raise RoleModeDeclarationError(
            f"@role_mode: expected a RoleMode member, got the class {mode.__qualname__} itself — "
            f"the parentheses are missing. Write @role_mode(RoleMode.ALIVE). Allowed: {_ALLOWED}."
        )

    def decorator(cls: _RT) -> _RT:
        if not isinstance(mode, RoleMode):
            raise RoleModeDeclarationError(
                f"@role_mode({cls.__qualname__}): expected a RoleMode member, got {mode!r}. Allowed: {_ALLOWED}."
            )
        cast(Any, cls)._role_mode_info = {"mode": mode}
        return cls

    return decorator


def report(label: str, factory: Callable[[], Any]) -> None:
    """Run one case and print its outcome."""
    try:
        result = factory()
        print(f"{label}: accepted -> {result!r}")
    except RoleModeDeclarationError as error:
        print(f"{label}: {type(error).__name__}: {error}")


report("wrong string", lambda: proposed_role_mode("alive")(type("ViewerRole", (), {})))
report("wrong number", lambda: proposed_role_mode(42)(type("CounterRole", (), {})))
report("none", lambda: proposed_role_mode(None)(type("EmptyRole", (), {})))


class Other(Enum):
    """Another closed set with the same string values."""

    ALIVE = "alive"


report("other enum", lambda: proposed_role_mode(Other.ALIVE)(type("ForeignRole", (), {})))


class Bare:
    """A role written with @role_mode and no parentheses."""


report("missing parentheses", lambda: proposed_role_mode(Bare))


class Good:
    """A role with a correct declaration."""


report("accepted member", lambda: proposed_role_mode(RoleMode.ALIVE)(Good))
print("stored verbatim:", Good._role_mode_info["mode"] is RoleMode.ALIVE)
