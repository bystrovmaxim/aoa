# packages/aoa-action-machine/src/aoa/action_machine/exceptions/action_result_type_error.py
"""ActionResultTypeError."""


class ActionResultTypeError(TypeError):
    """
    Summary or ``@on_error`` returned a value that is not the action's declared ``R``.

    Raised when runtime type does not match ``BaseAction[P, R]`` (e.g. wrong
    ``BaseResult`` subclass). Carries expected/actual types for adapters and tests.
    """

    def __init__(
        self,
        message: str,
        *,
        expected_type: type,
        actual_type: type,
    ) -> None:
        super().__init__(message)
        self.expected_type: type = expected_type
        self.actual_type: type = actual_type
