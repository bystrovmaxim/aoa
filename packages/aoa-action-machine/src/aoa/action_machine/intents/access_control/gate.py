# packages/aoa-action-machine/src/aoa/action_machine/intents/access_control/gate.py
"""
Gate — the five published names of the steps that decide access.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A refusal says which step refused, and it says it with one of five words. The
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
                          CHECK_ROLES       no role the operation lists is held
    2  the roles and
       their conditions   WHEN              a listed role is held, but every
                                            matching grant's ``when=`` refused
    3  the shared condition
                          GUARD             the operation's ``guard=`` refused
    4  the object         ACCESS_DECIDE     the object may not be touched

    ``CHECK_ROLES`` and ``WHEN`` are one step with two answers. The step searches
    grants and evaluates each grant's ``when=`` while it searches, because a
    grant whose role matches but whose condition says no is skipped and another
    grant may still win; a cascade that stops at the first refusal could not
    express that. The step is one, and the word a caller reads says which of the
    two it was: no such role, or a role whose condition refused.

    Refused(gate=Gate.…, reason=… | no reason) ──▶ event ──▶ whoever reads it

═══════════════════════════════════════════════════════════════════════════════
SCOPE (IN / OUT)
═══════════════════════════════════════════════════════════════════════════════

IN: the five names, and the rule that a name travels with a refusal — never the
class, the function or the module that happened to answer.

OUT: the order itself (held by ``cascade.GATES``), what each step decides, why a
developer's own condition refused (that is the developer's ``reason=``), and how
any transport presents a refusal.
"""

from __future__ import annotations

from enum import StrEnum


class Gate(StrEnum):
    """
    AI-CORE-BEGIN
        ROLE: Names what refused, in the words a caller branches on.
        CONTRACT: Exactly five values, each spelled as its own name, because the value is published and renaming one is a change to the contract; ``Refused.gate`` and ``Undecided.gate`` carry it.
        INVARIANTS: The member name and the value never diverge; being a ``str``, a value validates straight from the wire and serialises as itself.
    AI-CORE-END
    """

    AUTH_COORDINATOR = "AUTH_COORDINATOR"
    CHECK_ROLES = "CHECK_ROLES"
    WHEN = "WHEN"
    GUARD = "GUARD"
    ACCESS_DECIDE = "ACCESS_DECIDE"
