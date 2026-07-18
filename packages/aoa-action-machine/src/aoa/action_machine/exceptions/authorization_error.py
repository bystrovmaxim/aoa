# packages/aoa-action-machine/src/aoa/action_machine/exceptions/authorization_error.py
"""AuthorizationError."""


class AuthorizationError(Exception):
    """
    Authorization failure (insufficient role permissions).

    ``level`` is optional and set by the raiser: ``1`` (no role matched at all),
    ``2`` (a role matched but its grant's ``when=`` or the action's ``guard=``
    rejected the request), ``3`` (``access_decide`` rejected), or ``None`` when
    not specified (e.g. authentication failures raised outside ``RoleChecker``).

    ``reason`` is optional too, and — for level 1/2 — always set by
    ``RoleChecker``: the fixed ``"FORBIDDEN_ROLE"`` when no role matched, or the
    mandatory, developer-declared string that came with the ``when=``/``guard=``
    that rejected the request (see the ``check_roles``/``grant`` module
    docstrings). ``None`` means no gate populated it — today, that is level 3
    (``access_decide``'s own denial-reason mechanism is a separate, not-yet-done
    change) and any authorization failure raised outside ``RoleChecker``.
    """

    def __init__(self, message: str, *, level: int | None = None, reason: str | None = None) -> None:
        super().__init__(message)
        self.level = level
        self.reason = reason
