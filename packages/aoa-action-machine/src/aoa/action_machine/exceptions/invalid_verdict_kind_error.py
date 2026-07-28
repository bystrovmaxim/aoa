# packages/aoa-action-machine/src/aoa/action_machine/exceptions/invalid_verdict_kind_error.py
"""InvalidVerdictKindError."""


class InvalidVerdictKindError(ValueError):
    """
    Raised when an access-check answer is built with a `kind` that is not a non-empty
    string: missing, the wrong type, or nothing but whitespace.

    `kind` is the name the client reads to tell one answer from another. Blank, it
    matches nothing the client knows about, so a genuine refusal arrives looking like
    an answer nobody can act on. A name of spaces matches just as little as no name,
    and a number matches nothing at all.

    A ValueError so that a verdict read back as part of a larger payload fails as a
    normal validation error instead of escaping as an unhandled crash.
    """

    def __init__(self, verdict_class_name: str, given: object) -> None:
        super().__init__(
            f"{verdict_class_name}(kind={given!r}): kind is the name the client reads to tell "
            f"one answer from another, so it has to be a string with something in it. Give it a "
            f"real name, or leave it out to get the one this class already uses."
        )
        self.verdict_class_name = verdict_class_name
        self.given = given
