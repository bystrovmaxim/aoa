# src/action_machine/intents/meta/meta_intent_resolver.py
"""MetaIntentResolver — resolves normalized ``@meta`` declarations."""

from __future__ import annotations

from typing import Any


class MetaIntentResolver:
    """
    AI-CORE-BEGIN
    ROLE: Resolve class-level ``@meta`` declarations for graph model builders.
    CONTRACT: Reads normalized ``_meta_info`` scratch and returns only typed values needed by graph nodes.
    INVARIANTS: Does not validate decorator invariants and does not materialize graph nodes.
    AI-CORE-END
    """

    @staticmethod
    def meta_info_dict(host_cls: type) -> dict[str, Any]:
        """
        Return ``_meta_info`` written by ``@meta`` on ``host_cls``, or ``{}`` when absent or not a mapping.
        """
        raw = getattr(host_cls, "_meta_info", None)
        return raw if isinstance(raw, dict) else {}

    @staticmethod
    def resolve_domain_type(host_cls: type) -> type | None:
        """Return the domain type declared by ``@meta`` when present."""
        domain_cls = MetaIntentResolver.meta_info_dict(host_cls).get("domain")
        return domain_cls if isinstance(domain_cls, type) else None

    @staticmethod
    def resolve_description(host_cls: type) -> str | None:
        """Return the description declared by ``@meta`` when present."""
        description = MetaIntentResolver.meta_info_dict(host_cls).get("description")
        return description if isinstance(description, str) and description else None
