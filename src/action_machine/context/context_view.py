# src/action_machine/context/context_view.py
"""
ContextView — frozen object with controlled context-field access.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``ContextView`` is a mediator between aspect code and full ``Context``.
Runtime (``ActionProductMachine``) creates it for each aspect/error-handler call
that declares ``@context_requires``. It receives full ``Context`` plus
frozenset of allowed keys. Public method ``get(key)`` checks key membership in
allowed set and delegates value resolution to ``context.resolve(key)``.

═══════════════════════════════════════════════════════════════════════════════
LEAST-PRIVILEGE PRINCIPLE
═══════════════════════════════════════════════════════════════════════════════

Aspect gets access only to fields explicitly declared via
``@context_requires``. Accessing any other field immediately raises
``ContextAccessError``. This:

- makes context dependencies explicit in code;
- prevents accidental reads of sensitive fields;
- simplifies testing: only requested fields must be prepared.

═══════════════════════════════════════════════════════════════════════════════
FROZEN OBJECT
═══════════════════════════════════════════════════════════════════════════════

ContextView is fully immutable:
- ``__setattr__`` raises ``AttributeError`` (except initialization through
  ``object.__setattr__``).
- ``__delattr__`` raises ``AttributeError``.
- No mutation methods are exposed.
- ``__slots__`` is intentionally not used because custom ``__setattr__`` +
  ``__slots__`` makes static analysis around ``object.__setattr__`` harder.
  Class-level annotations are used instead.

This guarantees that aspect code cannot accidentally mutate context view state.

═══════════════════════════════════════════════════════════════════════════════
CUSTOM FIELDS
═══════════════════════════════════════════════════════════════════════════════

``UserInfo``, ``RequestInfo``, and ``RuntimeInfo`` may be extended by
inheritance with extra fields. ``ContextView`` does not validate key existence
at creation time — it validates only key membership in ``allowed_keys``.
Value resolution is delegated to ``context.resolve()`` with dot-path traversal.
If field does not exist, ``resolve()`` returns ``None``.

"""

from typing import Any

from action_machine.model.exceptions import ContextAccessError


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
