# packages/aoa-action-machine/src/aoa/action_machine/intents/access_control/gate.py
"""
Gate — the three published names of the steps that decide access.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A refusal says which step refused, and it says it with one of three words. The
words are published to whoever reads an answer, so a value here is a contract
rather than an internal label: a caller branches on it, and the framework needs
no second vocabulary for the same thing — the gate name is the word.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    The order the cascade runs the steps in (``cascade.GATES``):

    step                  word              when it is answered
    ──────────────────────────────────────────────────────────────────────────
    1  who is calling     AUTH_COORDINATOR  credentials were presented and rejected
    2  the roles held     CHECK_ROLES       no role the operation lists is held
    3  the object         ACCESS_DECIDE     the object may not be touched

    The removed words ``WHEN`` and ``GUARD`` no longer exist: a condition once
    declared beside a role or on the operation now lives in ``@access_decide`` and
    answers ``ACCESS_DECIDE``.

    Refused(gate=Gate.…, reason=… | no reason) ──▶ event ──▶ whoever reads it

═══════════════════════════════════════════════════════════════════════════════
SCOPE (IN / OUT)
═══════════════════════════════════════════════════════════════════════════════

IN: the three names, and the rule that a name travels with a refusal — never the
class, the function or the module that happened to answer.

OUT: the order itself (held by ``cascade.GATES``), what each step decides, and how
any transport presents a refusal.
"""

from __future__ import annotations

from enum import StrEnum


class Gate(StrEnum):
    """
    AI-CORE-BEGIN
        ROLE: Names what refused, in the words a caller branches on.
        CONTRACT: Exactly three values, each spelled as its own name, because the value is published and renaming one is a change to the contract; ``Refused.gate`` and ``Undecided.gate`` carry it.
        INVARIANTS: The member name and the value never diverge; being a ``str``, a value validates straight from the wire and serialises as itself.
    AI-CORE-END
    """

    AUTH_COORDINATOR = "AUTH_COORDINATOR"
    CHECK_ROLES = "CHECK_ROLES"
    ACCESS_DECIDE = "ACCESS_DECIDE"
