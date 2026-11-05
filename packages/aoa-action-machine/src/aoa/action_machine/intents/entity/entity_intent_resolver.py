# packages/aoa-action-machine/src/aoa/action_machine/intents/entity/entity_intent_resolver.py
"""EntityIntentResolver — resolves normalized ``@entity`` declarations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

# The module, not the name: see ``entity_decorator`` — ``base_resource`` may still be loading.
import aoa.action_machine.resources.base_resource as base_resource_module
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.exceptions.missing_entity_info_error import MissingEntityInfoError
from aoa.action_machine.intents.entity.entity_relation_intent_resolver import (
    EntityRelationIntentResolver,
    gather_entity_relation_intent_resolvers,
)
from aoa.action_machine.intents.entity.entity_specialization_intent_resolver import (
    EntitySpecializationIntentResolver,
    gather_entity_specialization_intent_resolvers,
)
from aoa.action_machine.intents.meta.meta_intent_resolver import MetaIntentResolver

if TYPE_CHECKING:
    from aoa.action_machine.resources.base_resource import BaseResource


class EntityIntentResolver:
    """
    AI-CORE-BEGIN
    ROLE: Resolve class-level ``@entity`` declarations for graph model builders (parallel to ``MetaIntentResolver``).
    CONTRACT: Reads ``_entity_info`` scratch; :meth:`resolve_description` requires a usable description; ``resource`` is required (:meth:`resolve_resource_type`) and the domain is the resource's ``@meta`` domain (:meth:`resolve_domain_type`). Entity→entity refs use :mod:`aoa.action_machine.intents.entity.entity_relation_intent_resolver` (:class:`~aoa.action_machine.intents.entity.entity_relation_intent_resolver.EntityRelationIntentResolver` rows).
    INVARIANTS: Does not validate decorator grammar at decorator time — only interchange resolution semantics. Declared rules of a specialization are **read** here, never checked: the build validator owns that.
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
    def resolve_resource_type(host_cls: type) -> type[BaseResource]:
        """Return the ``BaseResource`` subclass ``@entity`` names, or raise :exc:`MissingEntityInfoError`."""
        resource_cls = EntityIntentResolver.entity_info_dict(host_cls).get("resource")
        if isinstance(resource_cls, type) and issubclass(resource_cls, base_resource_module.BaseResource):
            return resource_cls
        raise MissingEntityInfoError(host_cls, key="resource")

    @staticmethod
    def resolve_domain_type(host_cls: type) -> type[BaseDomain]:
        """Return the domain of the entity's resource, read from the resource's ``@meta``."""
        return MetaIntentResolver.resolve_domain_type(EntityIntentResolver.resolve_resource_type(host_cls))

    @staticmethod
    def resolve_entity_relations(host_cls: type) -> list[EntityRelationIntentResolver]:
        """
        Fields on ``host_cls`` that reference other entities via relation containers.

        Uses :func:`~aoa.action_machine.intents.entity.entity_relation_intent_resolver.gather_entity_relation_intent_resolvers`.
        """
        return gather_entity_relation_intent_resolvers(host_cls)

    @staticmethod
    def resolve_entity_specializations(host_cls: type) -> list[EntitySpecializationIntentResolver]:
        """
        Fields on ``host_cls`` that point at one of N extension entities.

        Uses :func:`~aoa.action_machine.intents.entity.entity_specialization_intent_resolver.gather_entity_specialization_intent_resolvers`.
        Returns an empty list when the class declares no such field, and raises
        :exc:`~aoa.action_machine.domain.exceptions.SpecializationDeclarationError`
        when a declared one cannot be read.
        """
        return gather_entity_specialization_intent_resolvers(host_cls)
