# packages/aoa-action-machine/src/aoa/action_machine/intents/connection/connection_intent_resolver.py
"""ConnectionIntentResolver — resolves normalized ``@connection`` declarations."""

from __future__ import annotations


class ConnectionIntentResolver:
    """
    AI-CORE-BEGIN
    ROLE: Resolve class-level ``@connection`` declarations for graph model builders.
    CONTRACT: Returns declared resource types (and optional ``(type, key)`` pairs) in decorator storage order; does not materialize graph nodes.
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

    @staticmethod
    def resolve_connection_types_and_keys(host_cls: type) -> list[tuple[type, str]]:
        """Return ``(resource_type, connection_key)`` per ``@connection``, in declaration order."""
        connection_info = getattr(host_cls, "_connection_info", None)
        if not connection_info:
            return []
        pairs: list[tuple[type, str]] = []
        for connection in connection_info:
            connection_type = getattr(connection, "cls", None)
            key = getattr(connection, "key", None)
            if isinstance(connection_type, type) and isinstance(key, str):
                pairs.append((connection_type, key))
        return pairs
