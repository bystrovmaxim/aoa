# src/action_machine/exceptions/missing_check_roles_error.py
"""
MissingCheckRolesError — action class lacks required ``@check_roles`` scratch.
"""

from __future__ import annotations

from action_machine.system_core import TypeIntrospection


class MissingCheckRolesError(ValueError):
    """
    AI-CORE-BEGIN
    ROLE: Fail fast when interchange resolution needs ``_role_info['spec']``.
    CONTRACT: Raised from :meth:`~action_machine.intents.check_roles.check_roles_intent_resolver.CheckRolesIntentResolver.resolve_check_roles` when storage is absent.
    AI-CORE-END
    """

    def __init__(self, host_cls: type) -> None:
        qual = TypeIntrospection.full_qualname(host_cls)
        super().__init__(
            f"{qual} has no @check_roles declaration; `_role_info['spec']` is required.",
        )
        self.host_cls = host_cls
