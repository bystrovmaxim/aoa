# src/action_machine/logging/log_scope.py
"""
Dynamic kwargs-backed coordinates for the current log call site.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``LogScope`` describes where logging happens: machine, action, aspect or plugin
event, and nest level. Values are arbitrary kwargs turned into attributes; it is
not a Pydantic model. ``DotPathNavigator`` reads fields via ``__getitem__`` for
``{%scope.*}`` templates.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

Aspect logging (``ToolsBox`` / ``info`` / ``warning`` / ``critical``):
``ScopedLogger`` builds ``LogScope`` with:

- ``machine`` — machine class name (e.g. ``ActionProductMachine``).
- ``action`` — fully qualified action class name.
- ``aspect`` — aspect method name.
- ``nest_level`` — 0 root, 1 child ``box.run``, etc.

Plugin handlers (``log`` argument):

- ``machine``, ``plugin``, ``action``, ``event``, ``nest_level``.

Templates: ``{%scope.action}``, ``{%scope.nest_level}``, etc.

"""

from typing import Any


class LogScope:
    """
AI-CORE-BEGIN
    ROLE: Runtime scope carrier for ``{%scope.*}`` template namespace.
    CONTRACT: Preserve insertion order and expose dict-like read API.
    INVARIANTS: Dynamic attributes are constructor-defined; dotpath is cached.
    AI-CORE-END
"""

    _key_order: list[str]
    _cached_path: str | None

    def __init__(self, **kwargs: Any) -> None:
        """Bind each kwarg as an attribute; remember key order for dotpath."""
        for key, value in kwargs.items():
            object.__setattr__(self, key, value)
        object.__setattr__(self, "_key_order", list(kwargs.keys()))
        object.__setattr__(self, "_cached_path", None)

    def __getitem__(self, key: str) -> object:
        """Return attribute ``key``; ``KeyError`` if missing."""
        try:
            return getattr(self, key)
        except AttributeError:
            raise KeyError(key) from None

    def __contains__(self, key: str) -> bool:
        """True if ``key`` was passed at construction."""
        return key in self._key_order

    def get(self, key: str, default: object = None) -> object:
        """Like dict.get."""
        return getattr(self, key, default)

    def keys(self) -> list[str]:
        """Field names in creation order."""
        return list(self._key_order)

    def values(self) -> list[object]:
        """Field values in creation order."""
        return [getattr(self, k) for k in self._key_order]

    def items(self) -> list[tuple[str, object]]:
        """Pairs ``(name, value)`` in creation order."""
        return [(k, getattr(self, k)) for k in self._key_order]

    def as_dotpath(self) -> str:
        """
        Join non-empty values with ``.`` in kwargs order.

        Numbers become strings; ``None`` and ``""`` skipped. Result cached.
        """
        if self._cached_path is None:
            values = []
            for key in self._key_order:
                val = getattr(self, key, None)
                if val is not None and val != "":
                    values.append(str(val))
            object.__setattr__(self, "_cached_path", ".".join(values))
        return self._cached_path  # type: ignore[return-value]

    def to_dict(self) -> dict[str, Any]:
        """Ordered ``{field: value}`` for debugging or interop."""
        return {key: getattr(self, key) for key in self._key_order}
