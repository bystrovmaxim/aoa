# packages/aoa-action-machine/src/aoa/action_machine/plugin/ocel/exceptions/ocel_contract_error.py
"""OcelContractError — data/invariant contract violation."""

from aoa.action_machine.plugin.ocel.exceptions.ocel_error import OcelError


class OcelContractError(OcelError):
    """Raised when OCEL data or invariant contract is violated.

    Catch with: ``except OcelContractError``.
    """
