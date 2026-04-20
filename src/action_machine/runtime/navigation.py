# src/action_machine/runtime/navigation.py
"""
Unified dot-path navigation for nested objects across ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``DotPathNavigator`` resolves strings such as ``"user.address.city"`` against a
root object using a fixed strategy order. Callers include ``BaseSchema.resolve()``
and logging ``VariableSubstitutor`` so field access and template substitution share
the same rules for missing keys, ``None`` leaves, and attribute vs mapping access.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    resolve_step(current, segment)
         │
         ├── model-like (type.model_fields + __getitem__)  →  _step_schema
         ├── dict                                     →  _step_dict
         ├── other __getitem__                        →  _step_getitem
         └── else                                     →  _step_generic (getattr)

    navigate(root, "a.b.c")
         └── repeated resolve_step until _SENTINEL or leaf value

    navigate_with_source(root, dotpath)
         └── same steps; returns (value, parent_object, last_segment)

"""

from __future__ import annotations

from typing import Any

# Unique “missing” marker (never use None — it may be a valid value).
_SENTINEL: object = object()


def _is_model_like_mapping(obj: object) -> bool:
    """True for Pydantic-style models: class ``model_fields`` + instance ``__getitem__``."""
    cls = type(obj)
    return hasattr(cls, "model_fields") and hasattr(obj, "__getitem__")


class DotPathNavigator:
    """
AI-CORE-BEGIN
    ROLE: Single entry point for nested key/attribute walks.
    CONTRACT: Priority — model-like, ``dict``, ``__getitem__``, ``getattr``.
    INVARIANTS: Strategies are pure; ``_SENTINEL`` encodes absence.
    AI-CORE-END
"""

    @staticmethod
    def _step_schema(current: object, segment: str) -> object:
        """
        One step for model-like objects (``__getitem__`` with declared/extra keys).

        Returns:
            Field value or ``_SENTINEL`` if lookup fails.
        """
        try:
            return current[segment]  # type: ignore[index]
        except (KeyError, TypeError):
            return _SENTINEL

    @staticmethod
    def _step_dict(current: dict[str, Any], segment: str) -> object:
        """One step for plain ``dict`` (membership test, no exception churn)."""
        if segment in current:
            return current[segment]
        return _SENTINEL

    @staticmethod
    def _step_getitem(current: object, segment: str) -> object:
        """
        One step for non-dict objects that implement ``__getitem__`` (e.g. log scopes).

        Returns:
            Indexed value or ``_SENTINEL``.
        """
        try:
            return current[segment]  # type: ignore[index]
        except (KeyError, TypeError, IndexError):
            return _SENTINEL

    @staticmethod
    def _step_generic(current: object, segment: str) -> object:
        """Final fallback: attribute access."""
        return getattr(current, segment, _SENTINEL)

    @staticmethod
    def resolve_step(current: object, segment: str) -> object:
        """
        Dispatch one path segment using the fixed strategy order.

        Model-like objects are detected without importing ``BaseSchema``: the
        object's class must have ``model_fields``, and the instance must support
        ``__getitem__``. Standard ``dict`` does not define ``model_fields`` on
        the class, so it falls through to the dict branch.
        """
        if _is_model_like_mapping(current):
            return DotPathNavigator._step_schema(current, segment)
        if isinstance(current, dict):
            return DotPathNavigator._step_dict(current, segment)
        if hasattr(current, "__getitem__"):
            return DotPathNavigator._step_getitem(current, segment)
        return DotPathNavigator._step_generic(current, segment)

    @staticmethod
    def navigate(root: object, dotpath: str) -> object:
        """
        Walk ``dotpath`` from ``root``; return the final value or ``_SENTINEL``.

        Args:
            root: Starting object.
            dotpath: Dot-separated segments (e.g. ``"user.address.city"``).

        Returns:
            Resolved value or ``_SENTINEL`` if any segment is missing.
        """
        current = root
        for segment in dotpath.split("."):
            current = DotPathNavigator.resolve_step(current, segment)
            if current is _SENTINEL:
                return _SENTINEL
        return current

    @staticmethod
    def navigate_with_source(
        root: object,
        dotpath: str,
    ) -> tuple[object, object | None, str | None]:
        """
        Like ``navigate``, but also return the parent object and last segment name.

        Used when callers must inspect the container (e.g. ``@sensitive`` on a
        property host).

        Returns:
            ``(value, source, last_segment)``. For empty ``dotpath``:
            ``(root, None, None)``.
        """
        if not dotpath:
            return root, None, None

        segments = dotpath.split(".")
        current = root
        source: object | None = None

        for segment in segments:
            source = current
            current = DotPathNavigator.resolve_step(current, segment)
            if current is _SENTINEL:
                return _SENTINEL, source, segment

        return current, source, segments[-1]
