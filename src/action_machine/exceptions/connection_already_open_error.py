# src/action_machine/exceptions/connection_already_open_error.py
"""ConnectionAlreadyOpenError."""

from action_machine.exceptions.transaction_error import TransactionError


class ConnectionAlreadyOpenError(TransactionError):
    """Connection is already open (duplicate open attempt)."""

    pass
