# src/action_machine/intents/connection/connection_intent_resolver.py
"""ConnectionIntentResolver — resolves normalized ``@connection`` declarations."""

from __future__ import annotations


class ConnectionIntentResolver:
    """
    AI-CORE-BEGIN
    ROLE: Resolve class-level ``@connection`` declarations for graph model builders.
    CONTRACT: Returns declared resource types in decorator storage order and does not materialize graph nodes.
    INVARIANTS: Reads existing ``_connection_info`` scratch without validating decorator invariants.
    AI-CORE-END
    """

    @staticmethod
    def resolve_connection_types(host_cls: type) -> list[type]:
        """Return resource types declared by ``@connection``."""
        connection_info = getattr(host_cls, "_connection_info", None)
        if not connection_info:
            return []
        connection_types: list[type] = []
        for connection in connection_info:
            connection_type = getattr(connection, "cls", None)
            if isinstance(connection_type, type):
                connection_types.append(connection_type)
        return connection_types
