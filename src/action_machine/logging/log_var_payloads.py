# src/action_machine/logging/log_var_payloads.py
"""
Structured ``level`` / ``channels`` entries in log ``var``.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provide immutable payload objects for ``var["level"]`` and ``var["channels"]``
so templates consume stable string fields while runtime logic uses typed masks.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- ``mask`` fields are strongly typed (``Level`` / ``Channel``).
- ``name`` / ``names`` fields are template-facing display strings.
- Payloads are immutable dataclasses (``frozen=True``, ``slots=True``).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    ScopedLogger._emit(...)
          |
          +--> LogLevelPayload(mask=Level.*, name="INFO/...")
          +--> LogChannelPayload(mask=Channel mask, names="debug, business")
          |
          v
    var payload passed into LogCoordinator.emit(...)
          |
          +--> validation + filtering use .mask
          +--> templates read .name / .names

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Templates use explicit attributes:
- ``{%var.level.name}``
- ``{%var.channels.names}``

Bitmask logic uses ``.mask`` only (subscriptions, validation).

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- No validation is done inside payload classes themselves.
- Coordinator and channel/level validators enforce semantic correctness.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Typed bridge between human-readable templates and bitmask logic.
CONTRACT: Carry both mask and display label(s) in immutable payload objects.
INVARIANTS: Runtime logic reads masks; templates read names.
FLOW: ScopedLogger creates payloads -> coordinator validates -> loggers consume.
FAILURES: Invalid payload semantics are caught by coordinator validators.
EXTENSION POINTS: Add fields only if all template and validator callers agree.
AI-CORE-END
"""

from __future__ import annotations

from dataclasses import dataclass

from action_machine.logging.channel import Channel
from action_machine.logging.level import Level


@dataclass(frozen=True, slots=True)
class LogLevelPayload:
    """
    Single message level payload with logic and display projections.

    AI-CORE-BEGIN
    ROLE: Encapsulate per-message severity in var payload.
    CONTRACT: ``mask`` for logic, ``name`` for templates.
    INVARIANTS: Immutable value object.
    AI-CORE-END
    """

    mask: Level
    name: str


@dataclass(frozen=True, slots=True)
class LogChannelPayload:
    """
    Channel payload with bitmask and pre-rendered label list.

    AI-CORE-BEGIN
    ROLE: Encapsulate channel mask for matching and template rendering.
    CONTRACT: ``mask`` for routing, ``names`` for display.
    INVARIANTS: Immutable value object.
    AI-CORE-END
    """

    mask: Channel
    names: str
