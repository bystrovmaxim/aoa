# src/action_machine/intents/logging/level.py
"""
Severity level bitmask for log messages (how urgent).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``Level`` is an ``IntFlag``. Each emitted message carries exactly one level bit,
chosen from the method name: ``info``, ``warning``, or ``critical``. In a
subscription, a level mask means “match if the message level is any of these
bits”.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Exactly one of ``Level.info``, ``Level.warning``, ``Level.critical`` per message.
- ``level_label`` is for human-readable console prefixes (e.g. ``INFO``).

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

``Level.warning | Level.critical`` in ``subscribe`` accepts both severities.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

``validate_level`` rejects combined or unknown level masks for message ``var``.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Level enum + labels + validation for coordinator and subscriptions.
CONTRACT: Three bits; message level is single-bit; subscription may OR bits.
INVARIANTS: _SINGLE_LEVELS frozenset gates validate_level.
FLOW: ScopedLogger._emit sets level from method → coordinator validates → logger match.
FAILURES: ValueError from validate_level on bad message level.
EXTENSION POINTS: new levels need enum + validation + label rules.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from enum import IntFlag


class Level(IntFlag):
    """Log severity: info, warning, critical (one bit per message)."""

    info = 1
    warning = 2
    critical = 4


_SINGLE_LEVELS = frozenset({Level.info, Level.warning, Level.critical})

# Avoid ``level.name`` typing (``str | None`` in stubs); map known single-bit levels.
_LEVEL_LABELS: dict[int, str] = {
    int(Level.info): "INFO",
    int(Level.warning): "WARNING",
    int(Level.critical): "CRITICAL",
}


def level_label(level: Level) -> str:
    """Map ``Level.info`` → ``INFO`` for console-style output."""
    return _LEVEL_LABELS[int(level)]


def validate_level(value: Level) -> None:
    """Require exactly one of info / warning / critical (one bit)."""
    if value not in _SINGLE_LEVELS:
        raise ValueError(
            f"level must be exactly one of info/warning/critical, got {value}"
        )
