# src/action_machine/logging/log_var_payloads.py
"""
Structured ``level`` / ``channels`` entries in log ``var``.

Templates use explicit attributes, e.g. ``{%var.level.name}``, ``{%var.channels.names}``.
Bitmask logic uses ``.mask`` only (subscriptions, validation).
"""

from __future__ import annotations

from dataclasses import dataclass

from action_machine.logging.channel import Channel
from action_machine.logging.level import Level


@dataclass(frozen=True, slots=True)
class LogLevelPayload:
    """Single message level: ``mask`` for logic, ``name`` for templates (e.g. ``INFO``)."""

    mask: Level
    name: str


@dataclass(frozen=True, slots=True)
class LogChannelPayload:
    """Channel bitmask: ``mask`` for logic, ``names`` for templates (comma-separated)."""

    mask: Channel
    names: str
