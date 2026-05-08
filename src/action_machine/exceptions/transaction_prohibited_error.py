# src/action_machine/exceptions/transaction_prohibited_error.py
"""TransactionProhibitedError."""

from action_machine.exceptions.transaction_error import TransactionError


class TransactionProhibitedError(TransactionError):
    """
    Transaction control was attempted in a prohibited nested scope.
    """
