# packages/aoa-action-machine/src/aoa/action_machine/intents/access_control/undecided.py
"""
Undecided — the answer for "nobody could tell", with the failure kept in memory.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The third answer, and the one that must never be confused with a refusal: a step
that cannot tell did not decide that the caller may not pass. It names the step
that could not tell, and it keeps the failure itself in memory for whoever logs
it — the cause is never part of the answer, because the text of a failure is
diagnostic material, not a contract a caller reads.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    Verdict  (kind: str, frozen, extra="forbid")
      ├── Allowed    (kind="allowed")
      ├── Refused    (kind="refused",   gate, reason?)
      └── Undecided  (kind="undecided", gate, private cause)   ◀── this module

    a step that raises ──┐
                         ├──▶ Undecided(gate=…, cause=…) ──▶ failed-step event
    a step that answers ─┘                                  └──▶  the answer to
    "I cannot tell"                                             whoever asked

    The cause stays here: ``model_dump()`` and every wire form carry the word and
    the step alone. Because the cause is part of the object, two undecided answers
    compare equal only through ``model_dump()`` — which is the right comparison,
    since what a caller sees is the answer.

═══════════════════════════════════════════════════════════════════════════════
SCOPE (IN / OUT)
═══════════════════════════════════════════════════════════════════════════════

IN: the word ``undecided``, the step that could not tell, and the failure kept
privately for logging.

OUT: what is logged and where (the OpenTelemetry plugin does that), and which
transport outcome the answer turns into.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import PrivateAttr

from aoa.action_machine.intents.access_control.gate import Gate
from aoa.action_machine.intents.access_control.verdict import Verdict


class Undecided(Verdict):
    """
    AI-CORE-BEGIN
        ROLE: The answer for "nobody could tell", naming the step that could not decide.
        CONTRACT: Pins ``kind`` to the published word ``undecided``; ``gate`` names the step that could not tell; ``cause`` is a private attribute, reachable in memory for logging and absent from ``model_dump()`` and every wire form. Buildable as ``Undecided(Gate.GUARD, cause=exc)``. Two of these answers compare by what a caller sees (``model_dump()``), not by their causes: ``==`` includes the private cause, and two steps that failed differently still answered the same thing.
        INVARIANTS: Frozen and extra-forbidding; the cause never leaves the process, and this answer never reads as a refusal.
    AI-CORE-END
    """

    kind: Literal["undecided"] = "undecided"
    gate: Gate = Gate.ACCESS_DECIDE

    _cause: BaseException | None = PrivateAttr(default=None)

    def __init__(
        self,
        gate: Gate = Gate.ACCESS_DECIDE,
        *,
        cause: BaseException | None = None,
        **extra: Any,
    ) -> None:
        """Build an undecided answer for a step, keeping the failure in memory only.

        ``extra`` carries whatever a mapping validation hands over — ``model_validate``
        reaches this constructor with every field — so the word, the step and an
        unknown field all pass through to pydantic and are judged there. The cause
        is never one of them: it cannot arrive from the wire.
        """
        data: dict[str, Any] = {"kind": "undecided", "gate": gate, **extra}
        super().__init__(**data)
        self._cause = cause
