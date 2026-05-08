# packages/aoa-action-machine/src/aoa/action_machine/exceptions/naming_suffix_error.py
"""NamingSuffixError."""


class NamingSuffixError(TypeError):
    """
    ActionMachine naming invariant violation (required suffix).
    """

    pass
