# src/action_machine/intents/connection/__init__.py
"""Class-level ``@connection`` decorator and ``ConnectionInfo`` records."""

from __future__ import annotations

from action_machine.intents.connection.connection_decorator import ConnectionInfo, connection

__all__ = ["ConnectionInfo", "connection"]
