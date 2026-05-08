# packages/aoa-action-machine/src/aoa/action_machine/intents/entity/entity_intent.py
"""
EntityIntent — marker mixin and invariant validators for ``@entity``.
"""

from __future__ import annotations

from typing import Any, ClassVar


class EntityIntent:
    """
    AI-CORE-BEGIN
    ROLE: Marker mixin declaring eligibility for ``@entity``.
    CONTRACT: Presence in MRO is required by decorator target validation.
    INVARIANTS: Holds no methods or instance state; only class-level marker semantics.
    AI-CORE-END
    """

    _entity_info: ClassVar[dict[str, Any]]


# ═════════════════════════════════════════════════════════════════════════════
# @entity invariants (decorator + graph inspectors)
# ═════════════════════════════════════════════════════════════════════════════


def entity_info_is_set(cls: type) -> bool:
    """
    Graph invariant: class was decorated with ``@entity`` (has ``_entity_info``).

    Does not validate dict shape — only presence of the scratch attribute.
    """
    return getattr(cls, "_entity_info", None) is not None
