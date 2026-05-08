# src/action_machine/exceptions/missing_entity_info_error.py
"""
MissingEntityInfoError — required ``@entity`` field missing or invalid on a host class.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Raised by :class:`~action_machine.intents.entity.entity_intent_resolver.EntityIntentResolver`
when graph resolution needs a concrete ``@entity`` scratch value (typically
``description`` or ``domain``) and ``_entity_info`` does not supply a usable value.
"""

from __future__ import annotations

from action_machine.system_core.type_introspection import TypeIntrospection


class MissingEntityInfoError(ValueError):
    """
    AI-CORE-BEGIN
    ROLE: Fail fast when mandatory ``@entity`` data is absent for resolvers.
    CONTRACT: Carries ``host_cls`` and ``key`` (scratch field name such as ``description`` or ``domain``).
    AI-CORE-END
    """

    def __init__(self, host_cls: type, *, key: str) -> None:
        qual = TypeIntrospection.full_qualname(host_cls)
        super().__init__(
            f"{qual} has no usable @entity {key!r} required for graph metadata resolution.",
        )
        self.host_cls = host_cls
        self.key = key
