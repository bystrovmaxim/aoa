# packages/aoa-action-machine/src/aoa/action_machine/exceptions/abstract_verdict_error.py
"""AbstractVerdictError."""


class AbstractVerdictError(TypeError):
    """
    Raised when `BaseVerdict` is built directly instead of one of the answers under it.

    `BaseVerdict` holds only what every answer has in common. By itself it is neither a
    yes, nor a no, nor a "could not check", so nothing downstream can act on one.
    """

    def __init__(self, verdict_class_name: str) -> None:
        super().__init__(
            f"{verdict_class_name} cannot be built directly: it holds what every answer has "
            f"in common, not which answer this is. Build an AllowedVerdict, a "
            f"FailSecurityVerdict, or a FailErrorVerdict."
        )
        self.verdict_class_name = verdict_class_name
