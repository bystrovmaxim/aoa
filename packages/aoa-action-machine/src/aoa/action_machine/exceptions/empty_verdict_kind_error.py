# packages/aoa-action-machine/src/aoa/action_machine/exceptions/empty_verdict_kind_error.py
"""EmptyVerdictKindError."""


class EmptyVerdictKindError(ValueError):
    """
    Raised when an access-check answer is built with an empty or missing `kind`.

    `kind` is the name the client reads to tell one answer from another. Blank, it
    matches nothing the client knows about, so a genuine refusal arrives looking like
    an answer nobody can act on.
    """

    def __init__(self, verdict_class_name: str, given: object) -> None:
        super().__init__(
            f"{verdict_class_name}(kind={given!r}): kind is the name the client reads to tell "
            f"one answer from another, so it cannot be empty or None. Give it a name, or leave "
            f"it out to get the one this class already declares."
        )
        self.verdict_class_name = verdict_class_name
        self.given = given
