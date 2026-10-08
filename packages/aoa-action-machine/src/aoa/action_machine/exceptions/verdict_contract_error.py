# packages/aoa-action-machine/src/aoa/action_machine/exceptions/verdict_contract_error.py
"""``VerdictContractError`` — a condition answered with something that is not a Verdict."""

from __future__ import annotations


class VerdictContractError(TypeError):
    """
    A declared condition answered with something that is not a ``Verdict``. The three answers —
    ``Allowed``, ``Refused``, ``Undecided`` — are the whole vocabulary of the access cascade.
    """

    pass
