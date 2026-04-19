# src/action_machine/logging/channel.py
"""
Semantic channel bitmask for log messages (what the event is about).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``Channel`` is an ``IntFlag`` used as the first argument to ``info`` / ``warning``
/ ``critical``. Multiple topics in one message are expressed as a bitmask with
``|``. Subscriptions test intersection with ``&``.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Only the five defined bits are legal. Unknown bits in a mask are rejected.
- Zero mask is invalid (empty channels).
- Values are validated at emit and when building subscriptions.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    caller (Channel.* mask)
            |
            v
    validate_channels(mask)
            |
            +--> fail-fast on zero / unknown bits
            |
            v
    coordinator payload + logger subscriptions
            |
            v
    subscription matching via bit intersection (&)
            |
            v
    channel_mask_label(mask) for human-readable rendering

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

``Channel.debug | Channel.business`` — debug trace tied to business flow.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

``validate_channels`` raises ``TypeError`` or ``ValueError`` on bad input.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Channel enum + validation for logging pipeline.
CONTRACT: IntFlag with five bits; validate_channels enforces non-empty known mask.
INVARIANTS: int-based mask check uses _ALL_CHANNELS_MASK (IntFlag ~ is unsafe).
FLOW: caller passes Channel → ScopedLogger → coordinator → subscription match.
FAILURES: TypeError/ValueError from validate_channels.
EXTENSION POINTS: new channels require enum + _ALL_CHANNELS update + subscription tests.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from enum import IntFlag


class Channel(IntFlag):
    """
    Semantic log channel bitmask (debug, business, security, compliance, error).

    AI-CORE-BEGIN
    ROLE: Topic classifier for log routing/filtering.
    CONTRACT: Compose topics with bitwise OR and test via bitwise AND.
    INVARIANTS: Only declared enum bits are legal for validated masks.
    AI-CORE-END
    """

    debug = 1
    business = 2
    security = 4
    compliance = 8
    error = 16


_ALL_CHANNELS = (
    Channel.debug
    | Channel.business
    | Channel.security
    | Channel.compliance
    | Channel.error
)

# IntFlag: ``~_ALL_CHANNELS`` is not a usable unrestricted mask; use int bits.
_ALL_CHANNELS_MASK = int(_ALL_CHANNELS)

# Order for human-readable labels (comma-separated names in templates).
_CHANNEL_LABEL_ORDER: tuple[Channel, ...] = (
    Channel.debug,
    Channel.business,
    Channel.security,
    Channel.compliance,
    Channel.error,
)


def channel_mask_label(mask: Channel) -> str:
    """
    Comma-separated channel member names for a bitmask, e.g. ``"debug, business"``.

    Call after ``validate_channels`` (or on any mask with only defined bits).
    """
    v = int(mask)
    return ", ".join(
        name
        for c in _CHANNEL_LABEL_ORDER
        if (v & int(c)) != 0
        for name in (c.name,)
        if name is not None
    )


def validate_channels(value: Channel) -> None:
    """Require a non-empty mask containing only defined channel bits."""
    if not isinstance(value, int):
        raise TypeError(f"channels must be Channel, got {type(value).__name__}")
    v = int(value)
    if v == 0:
        raise ValueError("channels cannot be empty (zero mask)")
    if v & ~_ALL_CHANNELS_MASK:
        raise ValueError(f"channels contains unknown bits: {value}")
