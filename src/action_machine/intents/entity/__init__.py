# src/action_machine/intents/entity/__init__.py
# pylint: disable=undefined-all-variable,import-outside-toplevel
"""
Entity intent package — ``@entity`` marker, decorator, graph inspector.

``EntityGraphNode`` lives in :mod:`action_machine.graph_model.nodes.entity_graph_node` and is
re-exported from :mod:`action_machine.domain` to avoid a cycle with
:mod:`action_machine.domain.entity` (``BaseEntity`` ↔ ``EntityIntent``).
``DomainGraphNode`` is interchange for ``BaseDomain`` markers
(:mod:`action_machine.graph_model.nodes.domain_graph_node`).
"""

from __future__ import annotations

from typing import Any

from action_machine.intents.entity.entity_decorator import entity, entity_info_dict

# Resolver/intent before decorator: avoids ``decorator → domain.__init__`` while this
# ``__init__`` still awaits ``entity_decorator`` if it were imported first alongside other work.
from action_machine.intents.entity.entity_intent import EntityIntent, entity_info_is_set
from action_machine.intents.entity.entity_intent_resolver import EntityIntentResolver
from action_machine.intents.entity.entity_relation_intent_resolver import EntityRelationIntentResolver

__all__ = [
    "DomainGraphNode",
    "EntityIntent",
    "EntityIntentInspector",
    "EntityIntentResolver",
    "EntityRelationIntentResolver",
    "entity",
    "entity_info_dict",
    "entity_info_is_set",
]


def __getattr__(name: str) -> Any:
    """Lazy imports avoid cycles while :mod:`action_machine.domain.entity` loads ``EntityIntent``."""
    if name == "DomainGraphNode":
        from action_machine.graph_model.nodes.domain_graph_node import DomainGraphNode

        return DomainGraphNode
    if name == "EntityIntentInspector":
        from action_machine.legacy.entity_intent_inspector import EntityIntentInspector

        return EntityIntentInspector
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)


def __dir__() -> list[str]:
    return sorted(__all__)
