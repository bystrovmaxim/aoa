# packages/aoa-action-machine/src/aoa/action_machine/exceptions/connection_validation_error.py
"""ConnectionValidationError."""

from aoa.action_machine.exceptions.transaction_error import TransactionError


class ConnectionValidationError(TransactionError):
    """
    Provided ``connections`` payload does not match ``@connection`` declaration.
    """
