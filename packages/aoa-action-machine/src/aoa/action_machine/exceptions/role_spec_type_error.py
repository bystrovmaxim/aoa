# packages/aoa-action-machine/src/aoa/action_machine/exceptions/role_spec_type_error.py
"""``RoleSpecTypeError`` — a role specification is not a role."""

from __future__ import annotations


class RoleSpecTypeError(TypeError):
    """
    A role specification is not a ``BaseRole`` subclass or ``grant(...)``. Role names as strings
    are refused on purpose: a string cannot be checked against the role hierarchy.
    """

    pass
