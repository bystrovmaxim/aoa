# packages/aoa-action-machine/src/aoa/action_machine/exceptions/connection_not_open_error.py
"""ConnectionNotOpenError."""

from aoa.action_machine.exceptions.transaction_error import TransactionError


class ConnectionNotOpenError(TransactionError):
    """Connection is not open for requested operation."""
