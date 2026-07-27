# packages/aoa-action-machine/src/aoa/action_machine/intents/access_control/base_verdict.py
"""What every access-check answer has in common."""

from __future__ import annotations

from typing import Any

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

    # frozen: a verdict can never be edited after it is made. FORBIDDEN_OBJECT is a single
    # shared instance, so editing one in place would change what every other caller in the
    # process gets back.
    # forbid: a field nobody declared is refused, not quietly ignored. An "allowed" answer
    # that somehow arrived carrying a reason looks like a refusal to anyone who reads the
    # reason first.
    model_config = ConfigDict(extra="forbid", frozen=True)

    # The name of this answer, as the client sees it. Each concrete class sets its own, and
    # a value passed in is kept exactly as given. It is stored rather than taken from the
    # class name so that renaming a class does not change what clients already receive.
    #
    # It can never be empty, and that rule is written in two places on purpose. Here it
    # travels into the published schema, so the client's own generated validator refuses
    # an empty name as well. In __init__ it becomes a message that names the class and
    # the value, instead of a length complaint that names neither.
    #
    # Every concrete class repeats min_length: redeclaring the field to give it a name
    # replaces this declaration outright, constraint included.
    kind: str = Field(min_length=1)

    def __init__(self, **kwargs: Any) -> None:
        # A subclass passes its own class here, so only BaseVerdict itself is stopped.
        if self.__class__ is BaseVerdict:
            raise AbstractVerdictError(self.__class__.__name__)
        if "kind" in kwargs and not kwargs["kind"]:
            raise EmptyVerdictKindError(self.__class__.__name__, kwargs["kind"])
        super().__init__(**kwargs)
