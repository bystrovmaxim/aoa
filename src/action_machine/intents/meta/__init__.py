# src/action_machine/intents/meta/__init__.py
"""
Public entrypoint for meta intent contracts and decorator.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Exports the ``@meta`` decorator plus marker mixins used by inspectors and graph
validation to identify classes carrying action/resource metadata.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    user class declaration
           |
           v
    @meta(...)
           |
           v
    class carries meta markers/intents
           |
           v
    graph inspectors and validators consume metadata
           |
           v
    runtime graph assembly / adapters

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.intents.meta import meta

    @meta(description="Create order", domain=OrdersDomain)
    class CreateOrderAction(...):
        ...

    # Edge case: invalid meta args -> decorator raises validation error.
"""

from action_machine.intents.meta.meta_decorator import meta
from action_machine.legacy.action_meta_intent import ActionMetaIntent
from action_machine.legacy.resource_meta_intent import ResourceMetaIntent

__all__ = ["ActionMetaIntent", "ResourceMetaIntent", "meta"]
