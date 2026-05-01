# src/action_machine/intents/check_roles/check_roles_intent_resolver.py
"""CheckRolesIntentResolver — unpacks ``@check_roles`` storage on action classes."""

from __future__ import annotations

from action_machine.auth.any_role import AnyRole
from action_machine.auth.base_role import BaseRole
from action_machine.auth.none_role import NoneRole


class CheckRolesIntentResolver:
    """
    AI-CORE-BEGIN
    ROLE: Resolve declared role types from ``_role_info`` / ``spec`` without materializing graph nodes.
    CONTRACT: Single place for ``spec`` → concrete ``BaseRole`` types used by interchange edges and facet inspectors.
    INVARIANTS: ``NoneRole`` / ``AnyRole`` expand to empty; tuple members filtered to ``BaseRole`` subclasses.
    AI-CORE-END
    """

    @staticmethod
    def resolve_required_role_types(action_cls: type) -> tuple[type[BaseRole], ...]:
        """Return declared concrete roles for ``action_cls`` from ``_role_info`` ``spec``."""
        raw = getattr(action_cls, "_role_info", None)
        if not isinstance(raw, dict):
            return ()
        return CheckRolesIntentResolver.role_types_from_spec(raw.get("spec"))

    @staticmethod
    def role_types_from_spec(spec: object) -> tuple[type[BaseRole], ...]:
        """Map normalized ``@check_roles`` ``spec`` to a tuple of ``BaseRole`` types (may be empty)."""
        if spec in (NoneRole, AnyRole):
            return ()
        if isinstance(spec, type) and issubclass(spec, BaseRole):
            return (spec,)
        if isinstance(spec, tuple):
            return tuple(r for r in spec if isinstance(r, type) and issubclass(r, BaseRole))
        return ()
