# src/action_machine/intents/sensitive/sensitive_decorator.py
"""
``@sensitive`` — mark properties whose log output should be masked.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Intent-grammar hook for PII: attach masking config to a property getter.
``VariableSubstitutor`` reads ``_sensitive_config`` during ``{%...}`` resolution
and applies ``mask_value``.

═══════════════════════════════════════════════════════════════════════════════
MASKING RULE
═══════════════════════════════════════════════════════════════════════════════

::

    visible = min(max_chars, ceil(len(value) * max_percent / 100))

If ``visible >= len(value)``, return unchanged. Else: first ``visible``
characters plus five repeats of ``char``.

Parameters: ``enabled`` (default True), ``max_chars`` (default 3), ``char``
(default ``'*'``), ``max_percent`` (default 50, range 0–100).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

``@sensitive`` → ``fget._sensitive_config`` → inspector snapshot /
``get_sensitive_fields`` → ``VariableSubstitutor._get_property_config`` →
``mask_value`` → masked string in template output.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

::

    class UserAccount:
        @property
        @sensitive(True, max_chars=3, char="*", max_percent=50)
        def email(self) -> str:
            return self._email

    Template ``Email: {%context.account.email}`` → ``Email: max*****``.

═══════════════════════════════════════════════════════════════════════════════
ERRORS
═══════════════════════════════════════════════════════════════════════════════

``TypeError`` / ``ValueError`` from parameter validation or wrong decorator
target (see runtime messages).

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Property decorator storing masking config for log substitution.
CONTRACT: @sensitive(enabled, max_chars, char, max_percent) on getters.
INVARIANTS: config on fget; consumed only by VariableSubstitutor + inspectors.
FLOW: decorate → _sensitive_config → resolve path → mask_value.
FAILURES: validation at decorate time; masking never suppress errors silently.
EXTENSION POINTS: mask_value rules live in masking module.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

# ============================================================================
# Parameter validation helpers (split to reduce cyclomatic complexity)
# ============================================================================


def _validate_sensitive_params(
    enabled: bool,
    max_chars: int,
    char: str,
    max_percent: int,
) -> None:
    """
    Validate ``@sensitive`` decorator parameters.

    Called once at decorator creation time (before applying to target).
    Raises ``TypeError`` or ``ValueError`` when contract is violated.
    """
    if not isinstance(enabled, bool):
        raise TypeError(
            f"@sensitive: parameter enabled must be bool, "
            f"got {type(enabled).__name__}."
        )

    if not isinstance(max_chars, int):
        raise TypeError(
            f"@sensitive: parameter max_chars must be int, "
            f"got {type(max_chars).__name__}."
        )

    if max_chars < 0:
        raise ValueError(
            f"@sensitive: max_chars cannot be negative, got {max_chars}."
        )

    if not isinstance(char, str):
        raise TypeError(
            f"@sensitive: parameter char must be a string, "
            f"got {type(char).__name__}."
        )

    if len(char) != 1:
        raise ValueError(
            f"@sensitive: char must be exactly one character, "
            f"got {len(char)} characters: {char!r}."
        )

    if not isinstance(max_percent, int):
        raise TypeError(
            f"@sensitive: parameter max_percent must be int, "
            f"got {type(max_percent).__name__}."
        )

    if not 0 <= max_percent <= 100:
        raise ValueError(
            f"@sensitive: max_percent must be in range 0..100, "
            f"got {max_percent}."
        )


# ============================================================================
# Main decorator
# ============================================================================


def sensitive(
    enabled: bool = True,
    *,
    max_chars: int = 3,
    char: str = "*",
    max_percent: int = 50,
) -> Callable[[Any], Any]:
    """
    Property-level decorator that marks values as sensitive for log masking.

    Can be applied to ``property`` (in either order with ``@property``) or to
    callable getter functions that will later become properties.
    """
    # Validate arguments (delegated helper for lower complexity).
    _validate_sensitive_params(enabled, max_chars, char, max_percent)

    config = {
        "enabled": enabled,
        "max_chars": max_chars,
        "char": char,
        "max_percent": max_percent,
    }

    def decorator(target: Any) -> Any:
        """
        Inner decorator applied to property or callable target.
        """
        # Case 1: target is property (@sensitive above @property).
        if isinstance(target, property):
            fget = target.fget
            if fget is None:
                raise TypeError(
                    "@sensitive: received property without getter. "
                    "Ensure @sensitive is applied to a property with getter."
                )
            fget._sensitive_config = config  # type: ignore[attr-defined]
            # Return new property with same getter/setter/deleter/doc.
            return property(fget, target.fset, target.fdel, target.__doc__)

        # Case 2: target is callable (@property above @sensitive).
        if callable(target):
            target._sensitive_config = config
            return target

        # Unsupported target type.
        raise TypeError(
            f"@sensitive can only be applied to property objects or callables. "
            f"Got object of type {type(target).__name__}: {target!r}."
        )

    return decorator
