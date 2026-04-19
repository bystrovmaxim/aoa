# tests/runtime/_machine_plugins_helpers.py
"""Shared helpers for ActionProductMachine plugin event tests."""

from __future__ import annotations

from unittest.mock import AsyncMock

from action_machine.plugin.events import BasePluginEvent


def extract_event_types(mock_plugin_ctx: AsyncMock) -> list[str]:
    """Return event class names from recorded ``emit_event`` calls (positional arg 0)."""
    event_types: list[str] = []
    for call in mock_plugin_ctx.emit_event.call_args_list:
        event = call.args[0] if call.args else None
        if event is not None:
            event_types.append(type(event).__name__)
    return event_types


def extract_event(mock_plugin_ctx: AsyncMock, index: int) -> BasePluginEvent:
    """Return the event object from ``emit_event`` at the given call index."""
    return mock_plugin_ctx.emit_event.call_args_list[index].args[0]
