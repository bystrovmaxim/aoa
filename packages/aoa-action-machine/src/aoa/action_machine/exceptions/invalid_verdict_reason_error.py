# packages/aoa-action-machine/src/aoa/action_machine/exceptions/invalid_verdict_reason_error.py
"""InvalidVerdictReasonError."""


class InvalidVerdictReasonError(ValueError):
    """
    Raised when a refusal or a failed check is built with a `reason` that is not a
    non-empty string: missing, the wrong type, or nothing but whitespace.

    The reason is the only thing the caller gets to act on. Blank, it leaves them knowing
    they were stopped and nothing else, which is the same as not answering.

    A ValueError so that a verdict read back as part of a larger payload fails as a
    normal validation error instead of escaping as an unhandled crash.
    """

    def __init__(self, verdict_class_name: str, given: object) -> None:
        super().__init__(
            f"{verdict_class_name}(reason={given!r}): reason is the only thing the caller can "
            f"act on, so it has to be a string with something in it."
        )
        self.verdict_class_name = verdict_class_name
        self.given = given
