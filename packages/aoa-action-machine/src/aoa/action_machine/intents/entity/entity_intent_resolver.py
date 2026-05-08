# packages/aoa-action-machine/src/aoa/action_machine/intents/entity/entity_intent_resolver.py
"""EntityIntentResolver — resolves normalized ``@entity`` declarations."""

from __future__ import annotations

from typing import Any

from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.exceptions.missing_entity_info_error import MissingEntityInfoError
from aoa.action_machine.intents.entity.entity_relation_intent_resolver import (
    EntityRelationIntentResolver,
    gather_entity_relation_intent_resolvers,
)


class EntityIntentResolver:
    """
    AI-CORE-BEGIN
    ROLE: Resolve class-level ``@entity`` declarations for graph model builders (parallel to ``MetaIntentResolver``).
    CONTRACT: Reads ``_entity_info`` scratch; :meth:`resolve_description` requires a usable description; ``domain`` may be omitted (see :meth:`resolve_domain_optional` vs :meth:`resolve_domain_type`). Entity→entity refs use :mod:`aoa.action_machine.intents.entity.entity_relation_intent_resolver` (:class:`~aoa.action_machine.intents.entity.entity_relation_intent_resolver.EntityRelationIntentResolver` rows).
    INVARIANTS: Does not validate decorator grammar at decorator time — only interchange resolution semantics.
    FAILURES: :exc:`~aoa.action_machine.exceptions.MissingEntityInfoError` when a required resolved value is missing or invalid for the chosen API.
    AI-CORE-END
    """

    @staticmethod
    def entity_info_dict(host_cls: type) -> dict[str, Any]:
        """
        Return ``_entity_info`` written by ``@entity`` on ``host_cls``, or ``{}`` when absent or not a mapping.

        Kept identical to :func:`aoa.action_machine.intents.entity.entity_decorator.entity_info_dict`; duplicated here
        to avoid importing ``entity_decorator`` at module scope (cycles with ``EntityGraphNode`` / package ``__init__``).
        """
        raw = getattr(host_cls, "_entity_info", None)
        return raw if isinstance(raw, dict) else {}

    @staticmethod
    def resolve_description(host_cls: type) -> str:
        """Return stripped ``@entity`` ``description`` or raise :exc:`MissingEntityInfoError`."""
        description = EntityIntentResolver.entity_info_dict(host_cls).get("description")
        if not isinstance(description, str) or not description.strip():
            raise MissingEntityInfoError(host_cls, key="description")
        return description.strip()

    @staticmethod
    def resolve_domain_optional(host_cls: type) -> type[BaseDomain] | None:
        """
        Return the ``BaseDomain`` subclass from ``@entity`` when set, ``None`` when ``domain`` is unset/``None``.

        Raises:
            MissingEntityInfoError: ``domain`` is present but not a ``BaseDomain`` subclass.
        """
        domain_cls = EntityIntentResolver.entity_info_dict(host_cls).get("domain")
        if domain_cls is None:
            return None
        if isinstance(domain_cls, type) and issubclass(domain_cls, BaseDomain):
            return domain_cls
        raise MissingEntityInfoError(host_cls, key="domain")

    @staticmethod
    def resolve_domain_type(host_cls: type) -> type[BaseDomain]:
        """Return the ``BaseDomain`` subclass from ``@entity`` or raise :exc:`MissingEntityInfoError` (including when ``domain`` is ``None``)."""
        domain_cls = EntityIntentResolver.resolve_domain_optional(host_cls)
        if domain_cls is None:
            raise MissingEntityInfoError(host_cls, key="domain")
        return domain_cls

    @staticmethod
    def resolve_entity_relations(host_cls: type) -> list[EntityRelationIntentResolver]:
        """
        Fields on ``host_cls`` that reference other entities via relation containers.

        Uses :func:`~aoa.action_machine.intents.entity.entity_relation_intent_resolver.gather_entity_relation_intent_resolvers`.
        """
        return gather_entity_relation_intent_resolvers(host_cls)
