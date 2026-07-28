# packages/aoa-action-machine/src/aoa/action_machine/exceptions/authorization_error.py
"""AuthorizationError."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aoa.action_machine.intents.access_control import FailSecurityVerdict


class AuthorizationError(Exception):
    """
    Raised when a caller is not allowed to do something.

    Access is decided by three gates in a row, and ``level`` says which one refused:

    * ``1`` — the caller has none of the roles the action requires.
    * ``2`` — the caller has a role, but a condition attached to it turned the call down.
    * ``3`` — the action itself looked at the object in question and said no.
    * ``None`` — nobody reached those gates. Something in front of them refused first,
      such as the route's own authentication.

    ``verdict`` is that refusal as an object, carrying the reason to show the caller. It
    is ``None`` in exactly the same situation as ``level``: no gate ran, so no gate
    produced one.

    To display the reason, use the ``reason`` property below. It answers ``None`` when
    there is no verdict, so reading ``verdict.reason`` directly crashes in the one case
    the property already handles.
    """

    def __init__(self, message: str, *, level: int | None = None, verdict: FailSecurityVerdict | None = None) -> None:
        if not message and verdict is None:
            raise ValueError(
                "AuthorizationError: message and verdict cannot both be empty — "
                "an authorization failure must carry some description of what went wrong."
            )
        if verdict is not None:
            from aoa.action_machine.intents.access_control import FailSecurityVerdict

            if not isinstance(verdict, FailSecurityVerdict):
                raise TypeError(
                    f"AuthorizationError: verdict= must be a FailSecurityVerdict instance, "
                    f"got {type(verdict).__name__}."
                )
        super().__init__(message)
        self.level = level
        self.verdict = verdict

    @property
    def reason(self) -> str | None:
        """``verdict.reason``, or ``None`` if this failure carries no verdict at all."""
        return self.verdict.reason if self.verdict is not None else None
