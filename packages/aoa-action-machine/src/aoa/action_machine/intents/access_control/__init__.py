# packages/aoa-action-machine/src/aoa/action_machine/intents/access_control/__init__.py
"""Access-control verdict returned by ``machine.check`` without executing the action."""

from __future__ import annotations

from aoa.action_machine.intents.access_control.access_verdict import AccessVerdict, ResolveItemKind, kind_matches_reason

__all__ = ["AccessVerdict", "ResolveItemKind", "kind_matches_reason"]
