# packages/aoa-ocel/src/aoa/ocel/exceptions/ocel_contract_error.py
"""OcelContractError — data/invariant contract violation."""

from aoa.ocel.exceptions.ocel_error import OcelError


class OcelContractError(OcelError):
    """Raised when OCEL data or invariant contract is violated.

    Catch with: ``except OcelContractError``.
    """
