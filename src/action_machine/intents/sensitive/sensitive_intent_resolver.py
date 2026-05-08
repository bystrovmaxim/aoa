# src/action_machine/intents/sensitive/sensitive_intent_resolver.py
"""SensitiveIntentResolver — reads ``@sensitive`` scratch from class descriptors."""

from __future__ import annotations

from inspect import getattr_static
from typing import Any


class SensitiveIntentResolver:
    """
    AI-CORE-BEGIN
    ROLE: Collect ``_sensitive_config`` from properties and decorated callables on a host class.
    CONTRACT: ``resolve_sensitive_all_fields`` / ``resolve_sensitive_field`` return rows consumed by
        :class:`~action_machine.graph_model.nodes.sensitive_graph_node.SensitiveGraphPayload` / ``properties``
        (``sensitive_*`` keys); keys match public attribute names on ``host_cls``.
    INVARIANTS: Does not execute property getters; does not validate decorator invariants.
    AI-CORE-END
    """

    @staticmethod
    def resolve_sensitive_all_fields(
        host_cls: type,
    ) -> dict[str, dict[str, Any]]:
        """
        Return ``attribute_name ->`` sensitive row for each member that carries ``_sensitive_config``
        (written by :func:`~action_machine.intents.sensitive.sensitive_decorator.sensitive`).

        Values use graph-node keys: ``sensitive_enabled``, ``sensitive_max_chars``, ``sensitive_char``,
        ``sensitive_max_percent``, as produced by :meth:`resolve_sensitive_field` / :class:`~action_machine.graph_model.nodes.sensitive_graph_node.SensitiveGraphPayload`.
        """
        out: dict[str, dict[str, Any]] = {}
        for name in dir(host_cls):
            if name.startswith("_"):
                continue
            try:
                member = getattr_static(host_cls, name)
            except AttributeError:
                continue
            row = SensitiveIntentResolver._normalized_row_from_class_member(member)
            if row is not None:
                out[name] = row
        return out

    @staticmethod
    def resolve_sensitive_field(
        host_cls: type,
        field_name: str,
    ) -> dict[str, Any] | None:
        """
        Return the normalized sensitive row for a single public ``field_name``, or ``None`` when
        the attribute is missing, private, or has no ``@sensitive`` config.
        """
        needle = field_name.strip()
        if not needle or needle.startswith("_"):
            return None
        try:
            member = getattr_static(host_cls, needle)
        except AttributeError:
            return None
        return SensitiveIntentResolver._normalized_row_from_class_member(member)

    @staticmethod
    def _normalized_row_from_class_member(member: Any) -> dict[str, Any] | None:
        """Build graph-row dict from a class-level descriptor, or ``None`` if not sensitive."""
        fget: Any = None
        if isinstance(member, property):
            fget = member.fget
        elif callable(member):
            fget = member

        if fget is None or not hasattr(fget, "_sensitive_config"):
            return None

        raw = getattr(fget, "_sensitive_config", None)
        if not isinstance(raw, dict):
            return None

        return SensitiveIntentResolver._row_from_sensitive_config(raw)

    @staticmethod
    def _row_from_sensitive_config(cfg: dict[str, Any]) -> dict[str, Any]:
        """Map decorator keys ``enabled`` / ``max_chars`` / … to graph ``sensitive_*`` keys."""
        return {
            "sensitive_enabled": bool(cfg["enabled"]),
            "sensitive_max_chars": int(cfg["max_chars"]),
            "sensitive_char": str(cfg["char"]),
            "sensitive_max_percent": int(cfg["max_percent"]),
        }
