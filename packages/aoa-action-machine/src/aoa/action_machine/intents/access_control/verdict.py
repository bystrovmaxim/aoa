# packages/aoa-action-machine/src/aoa/action_machine/intents/access_control/verdict.py
"""
Verdict — the base of every access answer, carrying the contract word ``kind``.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Every access decision ends in exactly one answer, and every answer descends from
``Verdict``. The base declares a single field, ``kind``: a word of the published
contract rather than a class name, so renaming a class never changes what a
caller reads.

The base gives ``kind`` no default, so ``Verdict()`` cannot be constructed: an
answer has to say what it is. The three shapes — ``Allowed``, ``Refused`` and
``Undecided`` — each pin their own word with a ``Literal``.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    Verdict  (kind: str, frozen, extra="forbid")
      ├── Allowed    (kind="allowed")
      ├── Refused    (kind="refused",   gate, reason)
      └── Undecided  (kind="undecided", reason, private cause)

    decide() ──▶ Verdict ──▶ published event / raised exception / answer

The base is data only: no behaviour, no constructor guards, no hidden state. An
answer that breaks its own rules fails as a pydantic ``ValidationError`` naming
the field.

═══════════════════════════════════════════════════════════════════════════════
SCOPE (IN / OUT)
═══════════════════════════════════════════════════════════════════════════════

IN: the word every answer carries, the immutability of an answer, and the rule
that an answer never accepts a field it did not declare.

OUT: which word an answer carries (that is each subclass), what a refusal names,
and how any transport presents an answer.
"""

from __future__ import annotations

from pydantic import ConfigDict

from aoa.action_machine.model.base_schema import BaseSchema


class Verdict(BaseSchema):
    """
    AI-CORE-BEGIN
        ROLE: Base of the three access answers; carries the contract word ``kind``.
        CONTRACT: Frozen and extra-forbidding; ``kind`` has no default, and each subclass pins it with a ``Literal``. Subclasses add fields only, never behaviour.
        INVARIANTS: Immutable after construction; the word travels with the answer, the class name never does.
    AI-CORE-END
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: str
