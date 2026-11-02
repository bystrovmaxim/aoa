# packages/aoa-action-machine/src/aoa/action_machine/domain/event_marker.py
"""
EventMarker — what makes a class an event in the eyes of a domain.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A domain checks the classes in its ``events`` when it is defined. ``BaseEvent`` depends on
the domain, so the domain recognises an event by this marker and not by ``BaseEvent``.
"""

from __future__ import annotations


class EventMarker:
    """
    AI-CORE-BEGIN
    ROLE: Marks the classes a domain may list in ``events``.
    CONTRACT: ``BaseEvent`` is its only direct child, and every event descends from it.
    AI-CORE-END
    """
