# packages/aoa-action-machine/src/aoa/action_machine/exceptions/authorization_error.py
"""AuthorizationError."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Deferred: access_control transitively imports nearly the whole package (model,
    # context, auth) via model.base_schema -- and this module is itself imported from
    # deep inside that same chain (auth.base_role -> exceptions.naming_suffix_error ->
    # exceptions/__init__.py -> here), so a top-level import would cycle. `verdict` is
    # only ever stored/read, never constructed here, so no runtime import is needed at
    # all -- FailSecurityVerdict is only ever used as a type annotation below.
    from aoa.action_machine.intents.access_control import FailSecurityVerdict


class AuthorizationError(Exception):
    """
    Authorization failure (insufficient role permissions).

    ``level`` is optional and set by the raiser: ``1`` (no role matched at all),
    ``2`` (a role matched but its grant's ``when=`` or the action's ``guard=``
    rejected the request), ``3`` (``access_decide`` rejected), or ``None`` when
    not specified (e.g. authentication failures raised outside ``RoleChecker``).

    ``verdict`` is the ``FailSecurityVerdict`` this failure carries — set by
    ``RoleChecker`` for level 1/2 (``FailSecurityVerdict("FORBIDDEN_ROLE")``, or the
    ``when=``/``guard=`` grant's own reason), or by whatever raises this on
    ``access_decide``'s behalf for level 3. ``None`` for authorization failures raised
    outside the role cascade entirely (e.g. a route's own ``auth_coordinator``
    rejecting the caller before there is any role to check — ``aoa-fastapi-adapter``).
    Callers that need the reason as a bare string (e.g. building an HTTP error body)
    use the ``reason`` property below rather than reaching into ``verdict`` themselves.
    """

    def __init__(self, message: str, *, level: int | None = None, verdict: FailSecurityVerdict | None = None) -> None:
        if not message and verdict is None:
            raise ValueError(
                "AuthorizationError: message and verdict cannot both be empty — "
                "an authorization failure must carry some description of what went wrong."
            )
        super().__init__(message)
        self.level = level
        self.verdict = verdict

    @property
    def reason(self) -> str | None:
        """``verdict.reason``, or ``None`` if this failure carries no verdict at all."""
        return self.verdict.reason if self.verdict is not None else None
