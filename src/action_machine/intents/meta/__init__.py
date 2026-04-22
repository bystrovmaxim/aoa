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

"""

from __future__ import annotations

from typing import Any

from action_machine.intents.meta.action_meta_intent import ActionMetaIntent
from action_machine.intents.meta.resource_meta_intent import ResourceMetaIntent

__all__ = ["ActionMetaIntent", "ResourceMetaIntent", "meta"]


def __getattr__(name: str) -> Any:
    """Lazy ``meta`` import avoids cycles (``BaseAction`` → this package → ``meta_decorator`` → ``BaseDomain``)."""
    if name == "meta":
        from action_machine.intents.meta.meta_decorator import meta as meta_fn

        return meta_fn
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)


def __dir__() -> list[str]:
    return sorted(__all__)
