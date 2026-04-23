# src/action_machine/intents/connection/__init__.py
# pylint: disable=undefined-all-variable,import-outside-toplevel
"""Class-level ``@connection`` decorator, ``ConnectionInfo``, and ``ConnectionIntent``."""

from __future__ import annotations

from typing import Any

__all__ = ["ConnectionInfo", "ConnectionIntent", "connection"]


def __getattr__(name: str) -> Any:
    """Lazy imports avoid cycles (``connection_decorator`` ↔ ``BaseResource`` / ``resources``)."""
    if name == "ConnectionIntent":
        from action_machine.intents.connection.connection_intent import ConnectionIntent

        return ConnectionIntent
    if name == "ConnectionInfo":
        from action_machine.intents.connection.connection_decorator import ConnectionInfo

        return ConnectionInfo
    if name == "connection":
        from action_machine.intents.connection.connection_decorator import connection

        return connection
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)


def __dir__() -> list[str]:
    return sorted(__all__)
