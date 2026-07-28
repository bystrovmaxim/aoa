# packages/aoa-action-machine/src/aoa/action_machine/exceptions/access_denied_error.py
"""AccessDeniedError."""

from __future__ import annotations

from enum import IntEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aoa.action_machine.intents.access_control import FailSecurityVerdict


class AccessGate(IntEnum):
    """Which check refused a call.

    They run in this order, and the first one to say no stops the call there.

    The number, not the name, is what a transport publishes, so a client reading a
    denial reads the number. In code, use the name.
    """

    IDENTITY = 0
    """Nobody could tell who the caller is. Nothing further was even attempted."""

    ROLE = 1
    """The caller has none of the roles the action requires."""

    CONDITION = 2
    """The caller has a role, but a condition attached to it turned the call down."""

    OBJECT = 3
    """The action looked at the object in question and said no."""


class AccessDeniedError(Exception):
    """
    Raised when a call is refused before it runs.

    All three parts are required, because a refusal that cannot say who refused, or
    why, is not a refusal anybody can act on -- it is indistinguishable from a crash.

    * ``message`` is the sentence a person reads.
    * ``level`` is the :class:`AccessGate` that said no.
    * ``verdict`` carries the reason as a code a program can match on.

    A message and a reason are not interchangeable: one is for a reader, the other for
    a caller deciding what to do next. Both are always present.
    """

    def __init__(self, message: str, *, level: AccessGate, verdict: FailSecurityVerdict) -> None:
        from aoa.action_machine.intents.access_control import FailSecurityVerdict

        if not isinstance(message, str) or not message.strip():
            raise ValueError(
                f"AccessDeniedError: message= is the text shown when this is raised, so it has "
                f"to be a string with something in it. Got {message!r}."
            )
        # Checking the type as well as the value: anything merely EQUAL to a gate number
        # passes a membership test on its own, and True and 1.0 both are.
        if type(level) not in (int, AccessGate) or level not in tuple(AccessGate):
            raise ValueError(
                f"AccessDeniedError: level= names which check refused and must be an AccessGate "
                f"({', '.join(g.name for g in AccessGate)}). Got {level!r}."
            )
        if not isinstance(verdict, FailSecurityVerdict):
            raise TypeError(
                f"AccessDeniedError: verdict= carries the reason and must be a FailSecurityVerdict "
                f"instance, got {type(verdict).__name__}."
            )
        super().__init__(message)
        self.level = AccessGate(level)
        self.verdict = verdict

    @property
    def reason(self) -> str:
        """The verdict's reason -- the code a program matches on, not the message."""
        return self.verdict.reason
