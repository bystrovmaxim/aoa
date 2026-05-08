# src/action_machine/context/context_view.py
"""
ContextView — least-privilege read access to ``Context`` for ``@context_requires``.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Holds full ``Context`` plus a frozenset of allowed dot-path keys. ``get(key)``
delegates to ``context.resolve(key)`` when allowed; any other key raises
``ContextAccessError``. Immutable after construction. Missing paths resolve to
``None`` (membership in ``allowed_keys`` is checked, not whether the path exists).

"""

from typing import Any

from action_machine.exceptions.context_access_error import ContextAccessError


class ContextView:
    """
    Frozen guard object that exposes only declared context fields.
    """

    # Class-level annotations for static analyzers; actual assignment happens
    # via object.__setattr__ because __setattr__ is overridden as frozen guard.
    _context: Any
    _allowed_keys: frozenset[str]

    def __init__(self, context: Any, allowed_keys: frozenset[str]) -> None:
        """
        Initialize ContextView.

        Args:
            context: full execution Context, used for dot-path resolution.
            allowed_keys: frozenset of allowed dot-path keys declared via
                @context_requires. Empty set means no field access is allowed.
        """
        object.__setattr__(self, "_context", context)
        object.__setattr__(self, "_allowed_keys", allowed_keys)

    def get(self, key: str) -> Any:
        """
        Return context field value by dot-path key.

        Validates key membership in allowed set, then delegates to
        ``context.resolve(key)``.

        Args:
            key: dot-path key such as ``"user.user_id"`` or
                ``"request.trace_id"``.

        Returns:
            Resolved context value, or ``None`` if path does not exist.

        Raises:
            ContextAccessError: if key is not in allowed_keys.
        """
        if key not in self._allowed_keys:
            raise ContextAccessError(key, self._allowed_keys)
        return self._context.resolve(key)

    @property
    def allowed_keys(self) -> frozenset[str]:
        """
        Return allowed key set (read-only).
        """
        return self._allowed_keys

    def __setattr__(self, name: str, value: Any) -> None:
        """
        Forbid attribute assignment (frozen semantics).

        Raises:
            AttributeError: always.
        """
        raise AttributeError(
            f"ContextView is a frozen object. "
            f"Assignment of attribute '{name}' is not allowed."
        )

    def __delattr__(self, name: str) -> None:
        """
        Forbid attribute deletion (frozen semantics).

        Raises:
            AttributeError: always.
        """
        raise AttributeError(
            f"ContextView is a frozen object. "
            f"Deletion of attribute '{name}' is not allowed."
        )

    def __repr__(self) -> str:
        """Compact string representation for debugging."""
        keys_str = ", ".join(sorted(self._allowed_keys))
        return f"ContextView(allowed_keys=[{keys_str}])"
