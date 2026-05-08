# packages/aoa-action-machine/src/aoa/action_machine/logging/masking.py
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
