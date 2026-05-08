# packages/aoa-action-machine/src/aoa/action_machine/exceptions/missing_meta_error.py
"""
MissingMetaError — required ``@meta`` field missing or invalid on a host class.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Raised by :class:`~aoa.action_machine.intents.meta.meta_intent_resolver.MetaIntentResolver`
when graph resolution needs a concrete ``@meta`` scratch value (typically
``description`` or ``domain``) and ``_meta_info`` does not supply a usable value.
"""

from __future__ import annotations

from aoa.action_machine.system_core.type_introspection import TypeIntrospection


class MissingMetaError(ValueError):
    """
    AI-CORE-BEGIN
    ROLE: Fail fast when mandatory ``@meta`` data is absent for resolvers.
    CONTRACT: Carries ``host_cls`` and ``key`` (scratch field name such as ``description`` or ``domain``).
    AI-CORE-END
    """

    def __init__(self, host_cls: type, *, key: str) -> None:
        qual = TypeIntrospection.full_qualname(host_cls)
        super().__init__(
            f"{qual} has no usable @meta {key!r} required for graph metadata resolution.",
        )
        self.host_cls = host_cls
        self.key = key
