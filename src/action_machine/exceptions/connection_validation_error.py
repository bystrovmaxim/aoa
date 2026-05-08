# src/action_machine/exceptions/connection_validation_error.py
"""ConnectionValidationError."""

from action_machine.exceptions.transaction_error import TransactionError


class ConnectionValidationError(TransactionError):
    """
    Provided ``connections`` payload does not match ``@connection`` declaration.
    """
