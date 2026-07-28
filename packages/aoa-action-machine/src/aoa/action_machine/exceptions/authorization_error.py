# packages/aoa-action-machine/src/aoa/action_machine/exceptions/authorization_error.py
"""AuthorizationError."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Deferred: access_control pulls in most of the package, and that chain leads back
    # here, so importing it at the top raises ImportError.
    from aoa.action_machine.intents.access_control import FailSecurityVerdict


class AuthorizationError(Exception):
    """
    Authorization failure (insufficient role permissions).

    ``level`` says which of the three gates said no: ``1`` no role matched, ``2`` a role
    matched but a condition rejected the call, ``3`` ``access_decide`` rejected it.
    ``None`` when the refusal came from outside those gates.

    ``verdict`` is the refusal itself, and ``None`` for the same case. For the text
    alone, read ``reason`` below rather than reaching into it.
    """

    def __init__(self, message: str, *, level: int | None = None, verdict: FailSecurityVerdict | None = None) -> None:
        if not message and verdict is None:
            raise ValueError(
                "AuthorizationError: message and verdict cannot both be empty — "
                "an authorization failure must carry some description of what went wrong."
            )
        if verdict is not None:
            # pylint: disable-next=import-outside-toplevel
            from aoa.action_machine.intents.access_control import FailSecurityVerdict  # see TYPE_CHECKING note above

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
