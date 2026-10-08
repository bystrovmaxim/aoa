# packages/aoa-action-machine/src/aoa/action_machine/exceptions/signature_contract_error.py
"""``SignatureContractError`` — the method signature is not the one the intent requires."""

from __future__ import annotations


class SignatureContractError(TypeError):
    """
    The decorated method does not follow the signature contract of its intent: parameter count,
    names, order, annotations, or the types those annotations resolve to. The engine calls the
    method itself, so its signature is part of the contract, not the developer's private business.
    """

    pass
