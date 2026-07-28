# packages/aoa-action-machine/src/aoa/action_machine/intents/access_control/fail_error_verdict.py
"""Nobody could tell: the check itself broke."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from aoa.action_machine.exceptions.invalid_verdict_reason_error import InvalidVerdictReasonError
from aoa.action_machine.intents.access_control.base_verdict import BaseVerdict


class FailErrorVerdict(BaseVerdict):
    """
    AI-CORE-BEGIN
        ROLE: The "nobody could tell" of the three access-check answers — the check
              itself broke: a crash, a timeout, an operation nobody recognises.
        CONTRACT: Takes the reason first (``FailErrorVerdict("UNKNOWN_ENDPOINT")``);
                  kind is "FailErrorVerdict". The reason is a fixed code chosen by the
                  framework, never text taken from the failure.
        INVARIANTS: reason is present and never empty. Never treated or stored as a
                    refusal.
    AI-CORE-END

    This is not a refusal. Nobody decided anything -- the check never got an answer. Save
    it as a refusal and one brief database outage keeps saying "no" long after it ended.

    The reason is a fixed code, never the text of what broke. That text differs from one
    failure to the next, and whoever can see the difference can use it to work out what
    exists -- the same problem ``FORBIDDEN_OBJECT`` solves.

    This is what somebody who only *asked* is told. When the action really runs, anything
    that is not ``AllowedVerdict`` stops it.
    """

    # Same rule as kind, and stated in the same two places: the constraints reach the
    # client through the published schema, the constructor produces a message that
    # names the class and the value. min_length alone would accept a run of spaces.
    reason: str = Field(min_length=1, pattern=r"\S")

    def __init__(self, reason: str, kind: str = "FailErrorVerdict", **kwargs: Any) -> None:
        if not isinstance(reason, str) or not reason.strip():
            raise InvalidVerdictReasonError(self.__class__.__name__, reason)
        super().__init__(kind=kind, reason=reason, **kwargs)
