# packages/aoa-action-machine/src/aoa/action_machine/exceptions/role_mode_declaration_error.py
"""``RoleModeDeclarationError`` — a role carries no usable RoleMode metadata."""

from __future__ import annotations


class RoleModeDeclarationError(TypeError):
    """
    A role carries no usable ``RoleMode`` metadata: either ``@role_mode(...)`` was never applied,
    or the mode it recorded is not a ``RoleMode``.
    """

    pass
