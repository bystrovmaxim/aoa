# packages/aoa-action-machine/src/aoa/action_machine/intents/access_control/allowed.py
"""
Allowed — the answer that lets a call continue.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

One of the three answers a decision can end in, and the only one that lets the
call proceed. It carries no more than the word itself: a caller that may go
ahead has nothing to branch on, and a field nobody reads is a field that would
have to be kept stable for nobody.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    Verdict  (kind: str, frozen, extra="forbid")
      ├── Allowed    (kind="allowed")   ◀── this module
      ├── Refused    (kind="refused",   gate, reason)
      └── Undecided  (kind="undecided", gate, private cause)

    decide() ──▶ Allowed ──▶ the execution path runs the action
                        └──▶ the question path answers "it would be allowed"

═══════════════════════════════════════════════════════════════════════════════
SCOPE (IN / OUT)
═══════════════════════════════════════════════════════════════════════════════

IN: the published word ``allowed``, and the rule that this answer says nothing
else.

OUT: what happens after the answer — running the operation, publishing the
decision event, and how any transport presents it.
"""

from __future__ import annotations

from typing import Literal

from aoa.action_machine.intents.access_control.verdict import Verdict


class Allowed(Verdict):
    """
    AI-CORE-BEGIN
        ROLE: The answer that lets a call continue.
        CONTRACT: Pins ``kind`` to the published word ``allowed`` and adds no field of its own, because a caller that may proceed has nothing to branch on.
        INVARIANTS: Frozen and extra-forbidding, inherited from ``Verdict``; the word is the whole answer.
    AI-CORE-END
    """

    kind: Literal["allowed"] = "allowed"
