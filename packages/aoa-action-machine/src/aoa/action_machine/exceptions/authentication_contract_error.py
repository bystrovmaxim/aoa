# packages/aoa-action-machine/src/aoa/action_machine/exceptions/authentication_contract_error.py
"""AuthenticationContractError."""


class AuthenticationContractError(Exception):
    """
    A verified token violated the required-identifier contract.

    Raised when a JWT passes signature, expiry, issuer and audience verification
    but the configured ``user_id_claim`` or ``session_id_claim`` is missing,
    null, empty, whitespace-only or not a string. ``claim`` names the configured
    claim and ``reason`` states the validation failure; neither the token nor
    the claim's value is carried.
    """

    def __init__(self, claim: str, reason: str) -> None:
        """Store the claim name and the validation reason, never the value."""
        self.claim = claim
        self.reason = reason
        super().__init__(f"Required claim {claim!r} must be a non-blank string: {reason}.")
