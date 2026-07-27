# packages/aoa-action-machine/src/aoa/action_machine/intents/access_control/access_verdict.py
"""The three answers an access check can give: yes, no, and "could not check"."""

from __future__ import annotations

from typing import Any, Final

from pydantic import ConfigDict, Field

from aoa.action_machine.exceptions.abstract_verdict_error import AbstractVerdictError
from aoa.action_machine.exceptions.empty_verdict_kind_error import EmptyVerdictKindError
from aoa.action_machine.model.base_schema import BaseSchema


class BaseVerdict(BaseSchema):
    """
    AI-CORE-BEGIN
        ROLE: Abstract root of every access-check outcome — the shape that goes out
              over the wire, one flat class per outcome.
        CONTRACT: kind is a plain stored string, declared by each concrete class and
                  kept verbatim when a caller passes one; never empty. BaseVerdict
                  itself cannot be built directly.
        INVARIANTS: Forbid-extra fields, frozen.
    AI-CORE-END
    """

    # frozen: a verdict can never be edited after it is made. FORBIDDEN_OBJECT below is
    # a single shared instance, so editing one in place would change what every other
    # caller in the process gets back.
    # forbid: a field nobody declared is refused, not quietly ignored. An "allowed"
    # answer that somehow arrived carrying a reason looks like a refusal to anyone who
    # reads the reason first.
    model_config = ConfigDict(extra="forbid", frozen=True)

    # The name of this answer, as the client sees it. Each class below sets its own, and
    # a value passed in is kept exactly as given. It is stored rather than taken from the
    # class name so that renaming a class does not change what clients already receive.
    #
    # It can never be empty, and that rule is written in two places on purpose. Here it
    # travels into the published schema, so the client's own generated validator refuses
    # an empty name as well. In __init__ it becomes a message that names the class and
    # the value, instead of a length complaint that names neither.
    #
    # Every class below repeats min_length: redeclaring the field to give it a name
    # replaces this declaration outright, constraint included.
    kind: str = Field(min_length=1)

    def __init__(self, **kwargs: Any) -> None:
        # A subclass passes its own class here, so only BaseVerdict itself is stopped.
        if self.__class__ is BaseVerdict:
            raise AbstractVerdictError(self.__class__.__name__)
        if "kind" in kwargs and not kwargs["kind"]:
            raise EmptyVerdictKindError(self.__class__.__name__, kwargs["kind"])
        super().__init__(**kwargs)


class AllowedVerdict(BaseVerdict):
    """Yes, go ahead. Carries no reason at all: there is nothing to explain when nothing
    objected. This is what an action answers unless it says otherwise."""

    kind: str = Field(default="AllowedVerdict", min_length=1)


class FailSecurityVerdict(BaseVerdict):
    """No. The check ran, looked at who is asking, and refused.

    Write the reason first: ``FailSecurityVerdict("FORBIDDEN_ROLE")``. It cannot be
    empty -- a refusal that says nothing leaves the caller with nowhere to go.
    """

    kind: str = Field(default="FailSecurityVerdict", min_length=1)
    reason: str = Field(min_length=1)

    def __init__(self, reason: str, **kwargs: Any) -> None:
        kwargs["reason"] = reason
        super().__init__(**kwargs)


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
    """Nobody could tell. The check itself broke -- a crash, a timeout, an operation
    nobody recognises.

    This is not a refusal and must never be stored as one, or a single database hiccup
    would keep answering "no" long after it was over.

    The reason is a fixed code, never the text of whatever actually broke. That text
    differs from one failure to the next, and anyone who can see the difference can use
    it to map out what exists -- the same problem ``FORBIDDEN_OBJECT`` above solves.

    This is only what somebody who *asked* is told. When the action really runs,
    anything that is not ``AllowedVerdict`` stops it.
    """

    kind: str = Field(default="FailErrorVerdict", min_length=1)
    reason: str = Field(min_length=1)

    def __init__(self, reason: str, **kwargs: Any) -> None:
        kwargs["reason"] = reason
        super().__init__(**kwargs)
