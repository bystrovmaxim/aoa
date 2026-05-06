# src/action_machine/intents/meta/meta_intent_resolver.py
"""MetaIntentResolver — resolves normalized ``@meta`` declarations."""

from __future__ import annotations

from typing import Any

from action_machine.domain.base_domain import BaseDomain
from action_machine.exceptions import MissingMetaError


class MetaIntentResolver:
    """
    AI-CORE-BEGIN
    ROLE: Resolve class-level ``@meta`` declarations for graph model builders.
    CONTRACT: Reads normalized ``_meta_info`` scratch and returns only typed values needed by graph nodes.
    INVARIANTS: Does not validate decorator invariants and does not materialize graph nodes.
    FAILURES: :exc:`~action_machine.exceptions.MissingMetaError` from :meth:`resolve_description` or :meth:`resolve_domain_type` when the required scratch value is absent or invalid.
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
    def resolve_domain_type(host_cls: type) -> type[BaseDomain]:
        """Return the ``BaseDomain`` subclass from ``@meta`` or raise :exc:`MissingMetaError`."""
        domain_cls = MetaIntentResolver.meta_info_dict(host_cls).get("domain")
        if not isinstance(domain_cls, type) or not issubclass(domain_cls, BaseDomain):
            raise MissingMetaError(host_cls, key="domain")
        return domain_cls

    @staticmethod
    def resolve_description(host_cls: type) -> str:
        """Return stripped ``@meta`` ``description`` or raise :exc:`MissingMetaError`."""
        info = MetaIntentResolver.meta_info_dict(host_cls)
        raw = info.get("description")
        if not isinstance(raw, str) or not raw.strip():
            raise MissingMetaError(host_cls, key="description")
        return raw.strip()
