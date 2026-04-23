# src/action_machine/exceptions/naming_suffix_error.py
"""NamingSuffixError."""


class NamingSuffixError(TypeError):
    """
    ActionMachine naming invariant violation (required suffix).
    """

    pass
