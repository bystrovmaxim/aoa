# packages/aoa-action-machine/src/aoa/action_machine/intents/access_control/fail_security_verdict.py
"""No: somebody looked at who is asking and refused."""

from __future__ import annotations

from typing import Any, Final

from pydantic import Field

from aoa.action_machine.exceptions.invalid_verdict_reason_error import InvalidVerdictReasonError
from aoa.action_machine.intents.access_control.base_verdict import BaseVerdict


class FailSecurityVerdict(BaseVerdict):
    """
    AI-CORE-BEGIN
        ROLE: The "no" of the three access-check answers — the check ran, looked at who
              is asking, and refused. A real decision, safe to remember and reuse.
        CONTRACT: Takes the reason first (``FailSecurityVerdict("FORBIDDEN_ROLE")``);
                  kind is "FailSecurityVerdict". A subclass may add fields of its own
                  and still get the positional reason.
        INVARIANTS: reason is present and never empty.
    AI-CORE-END

    The reason is required. A refusal that says nothing leaves the caller with no idea
    what to do next.

    What the reason may say is a separate question. Sometimes a precise one tells an
    outsider something they should not learn -- see FORBIDDEN_OBJECT.
    """

    # Same rule as kind, and stated in the same two places: the constraints reach the
    # client through the published schema, the constructor produces a message that
    # names the class and the value. min_length alone would accept a run of spaces.
    reason: str = Field(min_length=1, pattern=r"\S")

    def __init__(self, reason: str, kind: str = "FailSecurityVerdict", **kwargs: Any) -> None:
        if not isinstance(reason, str) or not reason.strip():
            raise InvalidVerdictReasonError(self.__class__.__name__, reason)
        super().__init__(kind=kind, reason=reason, **kwargs)


# The one refusal for both "no such object" and "this object is not yours".
#
# The two must be indistinguishable: if they differ, someone can try IDs one by one and
# learn which objects exist for other people.
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
