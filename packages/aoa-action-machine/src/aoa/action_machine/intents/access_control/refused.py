# packages/aoa-action-machine/src/aoa/action_machine/intents/access_control/refused.py
"""
Refused — the answer that says no, naming what refused and why.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

One of the three answers a decision can end in, and the only one that stops the
call. It names the step that refused with one of the five published words, and
it carries the reason a developer declared beside the condition they wrote —
nothing else. The framework itself writes no reason text: a caller branches on
the word, and a reason, when it is there, is the developer's own.

This module also holds ``FORBIDDEN_OBJECT``, the one refusal an object-scoped
check returns: "there is no such object" and "it is not yours" are deliberately
the same answer, so that the error channel cannot be used to enumerate what
exists.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    Verdict  (kind: str, frozen, extra="forbid")
      ├── Allowed    (kind="allowed")
      ├── Refused    (kind="refused", gate, reason?)   ◀── this module
      └── Undecided  (kind="undecided", gate, private cause)

    decide() ──▶ Refused(gate=…, reason=…) ──▶ decision event ──▶ caller
                        │
                        └── FORBIDDEN_OBJECT is the shared instance an
                            ``access_decide()`` returns for a denied object

═══════════════════════════════════════════════════════════════════════════════
SCOPE (IN / OUT)
═══════════════════════════════════════════════════════════════════════════════

IN: the word ``refused``, the step that refused, the developer's reason, and the
shared object-scoped refusal.

OUT: which step refuses in a given situation (the steps decide), what a
transport does with the answer, and any vocabulary of reasons the framework
might have invented — it has none.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from aoa.action_machine.intents.access_control.gate import Gate
from aoa.action_machine.intents.access_control.verdict import Verdict


class Refused(Verdict):
    """
    AI-CORE-BEGIN
        ROLE: The answer that stops a call, naming what refused and the developer's reason.
        CONTRACT: Pins ``kind`` to the published word ``refused``; ``gate`` defaults to ``ACCESS_DECIDE``, the only step a developer writes; ``reason`` is the developer's declared text and stays absent when they declared none — non-empty and never whitespace-only when present. Buildable positionally: ``Refused("NOT_YOURS")``.
        INVARIANTS: Frozen and extra-forbidding, inherited from ``Verdict``; a refusal without a reason is valid, a refusal with an empty one is not.
    AI-CORE-END
    """

    kind: Literal["refused"] = "refused"
    gate: Gate = Gate.ACCESS_DECIDE
    reason: str | None = Field(default=None, min_length=1, pattern=r"\S")

    def __init__(
        self,
        reason: str | None = None,
        *,
        gate: Gate = Gate.ACCESS_DECIDE,
        **extra: Any,
    ) -> None:
        """Build a refusal from the developer's reason, defaulting the step to ``ACCESS_DECIDE``.

        ``extra`` carries whatever a mapping validation hands over — ``model_validate``
        reaches this constructor with every field — so the word, the step and an
        unknown field all pass through to pydantic and are judged there.
        """
        data: dict[str, Any] = {"kind": "refused", "gate": gate, "reason": reason, **extra}
        super().__init__(**data)


FORBIDDEN_OBJECT: Refused = Refused()
"""The one shared refusal for "no such object" and "someone else's object" (FR-011)."""
