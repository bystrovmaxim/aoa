# packages/aoa-action-machine/src/aoa/action_machine/intents/access_decide/access_decide_intent.py
"""
AccessDecideIntent — the marker that says an operation may declare an object check.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A marker only: it puts the declaration into the operation's own vocabulary, next
to the other intent markers every action carries, so that "this operation may
answer about its object" is part of what an action is rather than a method it
happens to have.

═══════════════════════════════════════════════════════════════════════════════
SCOPE (IN / OUT)
═══════════════════════════════════════════════════════════════════════════════

IN: the marker itself.

OUT: the decorator that declares the check (``access_decide_decorator``), the
resolver that finds it (``access_decide_intent_resolver``), and what the check
answers — that is the answer vocabulary, in ``intents/access_control``.
"""

from __future__ import annotations

from aoa.action_machine.intents.base_intent import BaseIntent


class AccessDecideIntent(BaseIntent):
    """
    AI-CORE-BEGIN
        ROLE: Declaration marker for an operation's object check.
        CONTRACT: Pure marker; the check itself is declared with the ``@access_decide`` decorator, and its absence is legitimate — an operation with no object check declares nothing.
        INVARIANTS: Carries no behaviour and no state.
    AI-CORE-END
    """

    pass
