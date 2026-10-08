# packages/aoa-action-machine/src/aoa/action_machine/exceptions/duplicate_access_decide_error.py
"""DuplicateAccessDecideError."""


class DuplicateAccessDecideError(TypeError):
    """
    Raised when an operation declares more than one object check.

    The object check is optional, but there is at most one per operation: two
    declarations mean two answers to the same question, and the operation cannot
    say which one decided.
    """

    pass
