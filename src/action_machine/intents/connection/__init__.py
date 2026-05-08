# src/action_machine/intents/connection/__init__.py
"""Class-level ``@connection`` decorator, ``ConnectionInfo``, and ``ConnectionIntent``."""

from __future__ import annotations

from action_machine.intents.connection.connection_decorator import ConnectionInfo, connection
from action_machine.intents.connection.connection_intent import ConnectionIntent

__all__ = ["ConnectionInfo", "ConnectionIntent", "connection"]
