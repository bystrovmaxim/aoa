# packages/aoa-action-machine/src/aoa/action_machine/exceptions/resource_contract_violation_error.py
"""ResourceContractViolationError — the caller's code broke the resource contract."""


class ResourceContractViolationError(RuntimeError):
    """
    AI-CORE-BEGIN
        ROLE: Base for a misuse of the resource contract by the caller's own code.
        CONTRACT: Raised where the caller's code broke an invariant the resource relies on, so the fix is in that code, not in the framework.
        INVARIANTS: Never describes an operational failure — those are ``HandleError``; a subclass raised while finalizing outranks the error of the run.
    AI-CORE-END
    """
