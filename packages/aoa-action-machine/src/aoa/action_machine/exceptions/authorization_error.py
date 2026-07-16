# packages/aoa-action-machine/src/aoa/action_machine/exceptions/authorization_error.py
"""AuthorizationError."""


class AuthorizationError(Exception):
    """
    Authorization failure (insufficient role permissions).

    ``level`` is optional and set by the raiser: ``1`` (no role matched at all),
    ``2`` (a role matched but its grant's ``when=`` or the action's ``guard=``
    rejected the request), or ``None`` when not specified (e.g. authentication
    failures raised outside ``RoleChecker``).
    """

    def __init__(self, message: str, *, level: int | None = None) -> None:
        super().__init__(message)
        self.level = level
