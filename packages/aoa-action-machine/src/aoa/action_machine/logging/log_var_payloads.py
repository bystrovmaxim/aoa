# packages/aoa-action-machine/src/aoa/action_machine/logging/log_var_payloads.py
"""
Structured ``level`` / ``channels`` entries in log ``var``.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provide immutable payload objects for ``var["level"]`` and ``var["channels"]``
so templates consume stable string fields while runtime logic uses typed masks.

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

"""

from __future__ import annotations

from dataclasses import dataclass

from aoa.action_machine.logging.channel import Channel
from aoa.action_machine.logging.level import Level


@dataclass(frozen=True, slots=True)
class LogLevelPayload:
    """
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
AI-CORE-BEGIN
    ROLE: Encapsulate channel mask for matching and template rendering.
    CONTRACT: ``mask`` for routing, ``names`` for display.
    INVARIANTS: Immutable value object.
    AI-CORE-END
"""

    mask: Channel
    names: str
