# packages/aoa-action-machine/src/aoa/action_machine/exceptions/authorization_error.py
"""AuthorizationError."""

from __future__ import annotations

from enum import IntEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aoa.action_machine.intents.access_control import FailSecurityVerdict


class AccessGate(IntEnum):
    """Which of the three checks refused a call.

    They run in this order, and the first one to say no stops the call.

    Numbers rather than names because the value is published in the HTTP body of a
    denial: a client already reading ``"level": 3`` keeps reading ``3``. In code, use
    the name.
    """

    ROLE = 1
    """The caller has none of the roles the action requires."""

    CONDITION = 2
    """The caller has a role, but a condition attached to it turned the call down."""

    OBJECT = 3
    """The action looked at the object in question and said no."""


class AuthorizationError(Exception):
    """
    Raised when a caller is not allowed to do something.

    ``level`` is the :class:`AccessGate` that refused, or ``None`` when nobody reached
    those gates -- something in front of them refused first, such as the route's own
    authentication.

    ``verdict`` is that refusal as an object, carrying the reason to show the caller. It
    is ``None`` in exactly the same situation as ``level``: no gate ran, so no gate
    produced one.

    To display the reason, use the ``reason`` property below. It answers ``None`` when
    there is no verdict, so reading ``verdict.reason`` directly crashes in the one case
    the property already handles.
    """

    def __init__(
        self, message: str, *, level: AccessGate | None = None, verdict: FailSecurityVerdict | None = None
    ) -> None:
        from aoa.action_machine.intents.access_control import FailSecurityVerdict

        if not isinstance(message, str) or not message.strip():
            raise ValueError(
                f"AuthorizationError: message= is the text shown when this is raised, so it has "
                f"to be a string with something in it. Got {message!r}."
            )
        # Checking the type as well as the value: anything merely EQUAL to 1, 2 or 3 passes
        # a membership test on its own, and True and 1.0 both are.
        if level is not None and (type(level) not in (int, AccessGate) or level not in tuple(AccessGate)):
            raise ValueError(
                f"AuthorizationError: level= names which gate refused and must be an AccessGate "
                f"({', '.join(g.name for g in AccessGate)}), or None when none of them ran. Got {level!r}."
            )
        if verdict is not None and not isinstance(verdict, FailSecurityVerdict):
            raise TypeError(
                f"AuthorizationError: verdict= must be a FailSecurityVerdict instance, "
                f"got {type(verdict).__name__}."
            )
        super().__init__(message)
        self.level = AccessGate(level) if level is not None else None
        self.verdict = verdict

    @property
    def reason(self) -> str | None:
        """``verdict.reason``, or ``None`` if this failure carries no verdict at all."""
        return self.verdict.reason if self.verdict is not None else None
