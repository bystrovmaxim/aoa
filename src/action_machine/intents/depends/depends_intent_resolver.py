# src/action_machine/intents/depends/depends_intent_resolver.py
"""DependsIntentResolver — resolves normalized ``@depends`` declarations."""

from __future__ import annotations


class DependsIntentResolver:
    """
    AI-CORE-BEGIN
    ROLE: Resolve class-level ``@depends`` declarations for graph model builders.
    CONTRACT: Returns declared dependency types in decorator storage order and does not materialize graph nodes.
    INVARIANTS: Reads existing ``_depends_info`` scratch without validating decorator invariants.
    AI-CORE-END
    """

    @staticmethod
    def resolve_dependency_types(host_cls: type) -> list[type]:
        """Return dependency types declared by ``@depends``."""
        depends_info = getattr(host_cls, "_depends_info", None)
        if not depends_info:
            return []
        dependency_types: list[type] = []
        for dependency_info in depends_info:
            dependency_type = getattr(dependency_info, "cls", None)
            if isinstance(dependency_type, type):
                dependency_types.append(dependency_type)
        return dependency_types
