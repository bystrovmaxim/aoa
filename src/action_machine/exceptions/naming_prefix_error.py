# src/action_machine/exceptions/naming_prefix_error.py
"""NamingPrefixError."""


class NamingPrefixError(TypeError):
    """
    ActionMachine naming invariant violation (required prefix).
    """

    pass
