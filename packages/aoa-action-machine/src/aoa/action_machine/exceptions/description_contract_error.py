# packages/aoa-action-machine/src/aoa/action_machine/exceptions/description_contract_error.py
"""``DescriptionContractError`` — a description is blank."""

from __future__ import annotations


class DescriptionContractError(ValueError):
    """
    A declared description is empty or whitespace-only. The intent is declared but says nothing,
    and a step nobody can read is a step nobody can review.
    """

    pass
