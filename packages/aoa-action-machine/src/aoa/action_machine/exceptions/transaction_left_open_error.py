# packages/aoa-action-machine/src/aoa/action_machine/exceptions/transaction_left_open_error.py
"""TransactionLeftOpenError — a resource was closed while a transaction was still open."""

from aoa.action_machine.exceptions.resource_contract_violation_error import ResourceContractViolationError


class TransactionLeftOpenError(ResourceContractViolationError):
    """
    AI-CORE-BEGIN
        ROLE: Raised when a resource is closed with a transaction still open.
        CONTRACT: The resource has already rolled the transaction back and returned its connection; the caller commits or rolls back before closing.
        INVARIANTS: Outranks the run's own error, which becomes its cause; only a cancellation wins over it.
    AI-CORE-END
    """
