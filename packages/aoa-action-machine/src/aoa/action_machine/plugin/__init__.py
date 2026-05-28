# packages/aoa-action-machine/src/aoa/action_machine/plugin/__init__.py
"""Plugin runtime (``plugin.core``) and optional built-in modules (e.g. ``plugin.ocel``)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aoa.action_machine.plugin.core import Plugin as Plugin

__all__ = ["Plugin"]


def __getattr__(name: str) -> object:
    """Lazy export so ``import plugin.ocel`` does not load ``plugin.core`` at init."""
    if name == "Plugin":
        from aoa.action_machine.plugin.core import Plugin

        return Plugin
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
