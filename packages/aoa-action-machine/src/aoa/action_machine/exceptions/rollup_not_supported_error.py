# packages/aoa-action-machine/src/aoa/action_machine/exceptions/rollup_not_supported_error.py
"""RollupNotSupportedError."""

from aoa.action_machine.exceptions.transaction_error import TransactionError


class RollupNotSupportedError(TransactionError):
    """
    Rollup mode is requested for a manager that cannot provide it.
    """
