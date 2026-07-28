# packages/aoa-action-machine/src/aoa/action_machine/exceptions/access_denied_error.py
"""AccessDeniedError."""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aoa.action_machine.intents.access_control import BaseVerdict


class AccessGate(StrEnum):
    """Which check refused a call.

    Each value names the thing a developer actually wrote, so a refusal says where to go
    and look. Listed in the order they run: the first to say no stops the call, and the
    ones after it never see it.
    """

    AUTH_COORDINATOR = "AUTH_COORDINATOR"
    """The ``auth_coordinator`` could not tell who is calling. This runs before any
    question of permissions, so nothing after it was even attempted."""

    CHECK_ROLES = "CHECK_ROLES"
    """``@check_roles`` on the action: the caller is known, and has none of the roles it
    lists."""

    WHEN_OR_GUARD = "WHEN_OR_GUARD"
    """A condition the developer attached alongside the role turned the call down --
    either ``grant(when=...)`` on one role, or ``guard=`` on the action as a whole."""

    ACCESS_DECIDE = "ACCESS_DECIDE"
    """``access_decide()`` on the action. Roles and conditions all passed; this looked at
    the particular object being touched -- whose order it is, say -- and said no."""


class AccessDeniedError(Exception):
    """
    Raised when a call is refused before it runs.

    All three parts are required, because a refusal that cannot say who refused, or
    why, is not a refusal anybody can act on -- it is indistinguishable from a crash.

    * ``message`` is the sentence a person reads.
    * ``refused_by`` is the :class:`AccessGate` that said no.
    * ``verdict`` carries the reason as a code a program can match on. Any verdict but an
      allow -- refusing a call is not only a security matter, and a feature flag turning
      something off is as good a reason as a role that did not match.

    A message and a reason are not interchangeable: one is for a reader, the other for
    a caller deciding what to do next. Both are always present.
    """

    def __init__(self, message: str, *, refused_by: AccessGate, verdict: BaseVerdict) -> None:
        from aoa.action_machine.intents.access_control import AllowedVerdict, BaseVerdict

        if not isinstance(message, str) or not message.strip():
            raise ValueError(
                f"AccessDeniedError: message= is the text shown when this is raised, so it has "
                f"to be a string with something in it. Got {message!r}."
            )
        if not isinstance(refused_by, AccessGate):
            raise ValueError(
                f"AccessDeniedError: refused_by= names which check said no and must be an AccessGate "
                f"({', '.join(AccessGate)}). Got {refused_by!r}."
            )
        if not isinstance(verdict, BaseVerdict) or isinstance(verdict, AllowedVerdict):
            raise TypeError(
                f"AccessDeniedError: verdict= carries the reason this call was refused, so it has "
                f"to be a verdict, and not an allow. Got {type(verdict).__name__}."
            )
        super().__init__(message)
        self.refused_by = refused_by
        self.verdict = verdict

    @property
    def reason(self) -> str:
        """The code a program matches on, not the message a person reads.

        A verdict is free to declare no reason text of its own; then its own name answers
        the same question, and there is always one.
        """
        return getattr(self.verdict, "reason", self.verdict.kind)
