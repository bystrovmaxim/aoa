# packages/aoa-action-machine/src/aoa/action_machine/intents/access_control/access_verdict.py
"""The three answers an access check can give: yes, no, and "could not check"."""

from __future__ import annotations

from typing import Any, Final

from pydantic import ConfigDict, Field

from aoa.action_machine.model.base_schema import BaseSchema


class BaseVerdict(BaseSchema):
    """
    AI-CORE-BEGIN
        ROLE: Abstract root of every access-check outcome — the shape that goes out
              over the wire, one flat class per outcome.
        CONTRACT: kind is always exactly type(self).__name__; cannot be instantiated directly.
        INVARIANTS: Forbid-extra fields, frozen.
    AI-CORE-END
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    # The default is only for mypy, which infers a constructor for subclasses that
    # define none. At runtime __init__ below always supplies a real value.
    kind: str = Field(default="")

    def __init__(self, **kwargs: Any) -> None:
        expected_kind = type(self).__name__
        given_kind = kwargs.pop("kind", expected_kind)
        if given_kind != expected_kind:
            raise ValueError(
                f"kind must be {expected_kind!r} for {expected_kind} (it is derived from the "
                f"class being constructed, not a free field) -- got {given_kind!r}."
            )
        # mypy checks this call against BaseSchema, which declares no fields, so it
        # does not see `kind`. Pydantic validates against the real class at runtime.
        super().__init__(kind=expected_kind, **kwargs)  # type: ignore[call-arg]

    # pylint infers a 0-argument signature for this hook; the real pydantic one takes
    # a context argument, which is what this matches.
    # pylint: disable-next=arguments-differ
    def model_post_init(self, __context: Any) -> None:
        # isinstance() would match subclasses too. Only BaseVerdict itself is abstract.
        if type(self) is BaseVerdict:  # pylint: disable=unidiomatic-typecheck
            raise TypeError(f"{type(self).__name__} is abstract and cannot be instantiated directly.")


class AllowedVerdict(BaseVerdict):
    """Yes. No ``reason`` field at all -- there is nothing to explain when nothing
    rejected the call. Also what ``BaseAction.access_decide()`` returns by default."""


class FailSecurityVerdict(BaseVerdict):
    """No: the check ran, looked at who is asking, and refused.

    ``reason`` is mandatory and non-empty. It can be constructed positionally
    (``FailSecurityVerdict("FORBIDDEN_ROLE")``) or by keyword -- pydantic calls
    ``__init__`` with keywords when deserializing, so both must work. A subclass may
    add fields and still get the positional ``reason`` without writing its own
    ``__init__``.
    """

    reason: str = Field(min_length=1)

    def __init__(self, reason: str, **kwargs: Any) -> None:
        super().__init__(reason=reason, **kwargs)


# The one answer for both "no such object" and "this object is not yours". They must
# be indistinguishable: if they differ, someone can try IDs one by one and learn which
# objects exist for other people.
#
# Decide both in a single condition, not in two steps:
#
#     if order is None or order.owner != caller:
#         return FORBIDDEN_OBJECT
#
# Two separate branches would return the same verdict today but leak later. They get
# edited at different times, so one of them eventually gets a more specific message;
# and the "missing" branch returns without doing the ownership lookup, so it answers
# faster -- the same leak, measured on the clock instead of read in the text.
#
# Once ownership is confirmed, a specific reason is safe: the caller already proved
# the object is theirs, so a precise message tells them nothing about anyone else.
FORBIDDEN_OBJECT: Final = FailSecurityVerdict("FORBIDDEN_OBJECT")


class FailErrorVerdict(BaseVerdict):
    """The check could not be answered -- a crash, a timeout, an unknown operation.

    Not a denial, and never cached as one: otherwise one database hiccup would keep
    answering "no" long after it was over. The reason is a fixed code, never the
    exception's own text, for the same purpose ``FORBIDDEN_OBJECT`` serves -- a
    distinguishable failure message is something to probe.

    This only affects what a caller who merely *asked* sees. On the real execution
    path anything other than ``AllowedVerdict`` still blocks the action.
    """

    reason: str = Field(min_length=1)

    def __init__(self, reason: str, **kwargs: Any) -> None:
        super().__init__(reason=reason, **kwargs)
