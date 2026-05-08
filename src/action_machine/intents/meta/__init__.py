# src/action_machine/intents/meta/__init__.py
"""
Public entrypoint for meta intent contracts and decorator.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Exports the ``@meta`` decorator plus the ``MetaIntent`` marker mixin used by
inspectors and graph validation for classes carrying metadata.

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

"""

from __future__ import annotations

from action_machine.intents.meta.meta_decorator import meta
from action_machine.intents.meta.meta_intent import MetaIntent

__all__ = ["MetaIntent", "meta"]
