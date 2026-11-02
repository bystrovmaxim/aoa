# packages/aoa-action-machine/src/aoa/action_machine/intents/emits/__init__.py
"""
Emits intent — the events one method of an action may emit.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Exports ``emits``. See ``emits_decorator`` for the rule.
"""

from aoa.action_machine.intents.emits.emits_decorator import emits

__all__ = ["emits"]
