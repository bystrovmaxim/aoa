# src/action_machine/logging/masking.py
"""
Masking utilities for sensitive data in logs.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provides the core masking function used by both the debug inspector and the
variable substitutor to hide sensitive values in rendered logs.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    @sensitive metadata / debug inspection
                   |
                   v
    mask_value(value, config)
                   |
                   +--> normalize config defaults
                   +--> compute keep length
                   +--> return visible prefix + mask suffix
                   |
                   v
    substituted/debug output in final log line

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    mask_value("4111111111111111", {"max_chars": 4, "char": "*", "max_percent": 50})
    # -> "4111*****"

    mask_value("abc", {"max_chars": 10, "max_percent": 100})
    # -> "abc"  (no masking when keep >= length)

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Shared low-level masker for logging privacy controls.
CONTRACT: Return deterministic partially-masked string based on config bounds.
INVARIANTS: Prefix keep length is min(chars-bound, percent-bound, length).
FLOW: raw value -> stringify -> compute keep -> append fixed mask suffix.
FAILURES: No exceptions for malformed config types; defaults are applied.
EXTENSION POINTS: Adjust masking strategy centrally without changing callers.
AI-CORE-END
"""

from typing import Any


def mask_value(value: Any, config: dict[str, Any]) -> str:
    """
    Mask value using ``max_chars``, ``char``, and ``max_percent`` constraints.
    """
    s = str(value)

    # Extract and validate config values
    max_chars = config.get("max_chars", 3)
    max_chars = int(max_chars) if isinstance(max_chars, int) else 3

    char = config.get("char", "*")
    char = str(char) if isinstance(char, str) else "*"

    max_percent = config.get("max_percent", 50)
    max_percent = int(max_percent) if isinstance(max_percent, int) else 50

    length = len(s)
    by_chars = min(max_chars, length)
    by_percent = int((length * max_percent + 99) // 100)  # ceil division
    keep = min(by_chars, by_percent)

    if keep >= length:
        return s

    visible = s[:keep]
    return visible + (char * 5)
