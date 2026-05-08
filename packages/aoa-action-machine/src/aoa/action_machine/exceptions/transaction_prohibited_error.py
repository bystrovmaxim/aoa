# packages/aoa-action-machine/src/aoa/action_machine/exceptions/transaction_prohibited_error.py
"""TransactionProhibitedError."""

from aoa.action_machine.exceptions.transaction_error import TransactionError


class TransactionProhibitedError(TransactionError):
    """
    Transaction control was attempted in a prohibited nested scope.
    """
