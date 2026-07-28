# packages/aoa-action-machine/src/aoa/action_machine/exceptions/allowed_verdict_as_reason_error.py
"""AllowedVerdictAsReasonError."""


class AllowedVerdictAsReasonError(ValueError):
    """
    Raised when a refusal is given an allow as the reason it refused.

    The type is right -- an allow is a verdict like any other -- so this is not a wiring
    mistake but a contradiction: "refused, and the reason is that it was permitted".

    It matters because the verdict travels. Asked "may I do this?", the machine hands the
    verdict from the refusal straight back to whoever asked. An allow in there answers
    "yes" to a call that was in fact refused, and a screen would enable a button nobody
    is allowed to press.
    """

    def __init__(self, verdict_class_name: str) -> None:
        super().__init__(
            f"AccessDeniedError: verdict= is the reason this call was refused, so it cannot be "
            f"{verdict_class_name}, which says the opposite. Whoever asks would be told the call "
            f"is permitted."
        )
        self.verdict_class_name = verdict_class_name
