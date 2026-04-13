# src/action_machine/logging/masking.py
"""
Masking utilities for sensitive data in logs.

Provides the core masking function used by both the debug inspector
and the variable substitutor to hide sensitive information.
"""

from typing import Any


def mask_value(value: Any, config: dict[str, Any]) -> str:
    """
    Mask a value according to the provided configuration.

    Args:
        value: The raw value (converted to string).
        config: Dictionary with keys:
            - 'enabled' (bool, ignored here – checked by caller)
            - 'max_chars' (int, default 3)
            - 'char' (str, default '*')
            - 'max_percent' (int, default 50)

    Returns:
        A masked string representation of the value.

    The algorithm shows at most `max_chars` characters or `max_percent`
    percent of the string length, whichever is smaller. The remainder
    is replaced with 5 copies of the `char` character.
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
