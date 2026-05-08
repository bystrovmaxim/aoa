# src/action_machine/exceptions/connection_not_open_error.py
"""ConnectionNotOpenError."""

from action_machine.exceptions.transaction_error import TransactionError


class ConnectionNotOpenError(TransactionError):
    """Connection is not open for requested operation."""
