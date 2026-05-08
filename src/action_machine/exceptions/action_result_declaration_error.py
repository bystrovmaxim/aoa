# src/action_machine/exceptions/action_result_declaration_error.py
"""ActionResultDeclarationError."""


class ActionResultDeclarationError(TypeError):
    """
    ``BaseAction[P, R]`` result type is missing, not a ``BaseResult`` subclass,
    or not resolvable from generics / forward references.
    """

    pass
