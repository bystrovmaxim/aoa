# packages/aoa-action-machine/src/aoa/action_machine/exceptions/role_mode_declaration_error.py
"""``RoleModeDeclarationError`` — a role's mode is unusable: not a member, missing, or unreadable."""

from __future__ import annotations


class RoleModeDeclarationError(TypeError):
    """
    AI-CORE-BEGIN
    ROLE: Refuse a role whose lifecycle mode is unusable, at the moment the fault becomes visible.
    CONTRACT: Raised by ``@role_mode`` for an argument that is not a ``RoleMode`` member or for the bare form, and by ``RoleMode.declared_for`` for a role with no metadata or with a mode that is not a member.
    INVARIANTS: The message names the role; the decorator's refusal also names the value received and all four members.
    AI-CORE-END
    """
