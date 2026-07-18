# packages/aoa-action-machine/src/aoa/action_machine/intents/access_control/access_verdict.py
"""AccessVerdict — result of an access check without executing the action."""

from __future__ import annotations

from enum import StrEnum
from typing import Self

from pydantic import ConfigDict, model_validator

from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.model.base_schema import BaseSchema


class ResolveItemKind(StrEnum):
    """
    Source channel a resolve answer came through — not a stability/severity ranking.

    Canonical home for this enum: it is what an access check actually decides, one
    layer below the wire (``aoa-fastapi-adapter``'s ``ResolveItemResult`` reuses it,
    never redefines it). ``SUCCESS``/``SECURITY``/``FLAG``/``MACHINE_RULE`` are
    settled answers that will not change on their own; ``CHECK_ERROR`` is the
    absence of an answer (the resolver never reached a decision — an unknown
    endpoint, a timeout, a crash), so it must never be treated as a denial or
    cached as one. ``CHECK_ERROR`` is not produced by an access check itself
    (see ``AccessVerdict`` below) — the resolver adds it around the check, when
    the check was never reached at all.
    """

    SUCCESS = "success"
    SECURITY = "security"
    FLAG = "flag"
    MACHINE_RULE = "machine_rule"
    CHECK_ERROR = "check_error"


class AccessVerdict(BaseSchema):
    """
    AI-CORE-BEGIN
        ROLE: Answer "can this run?" without executing the action.
        CONTRACT: kind=SUCCESS implies reason=""; every other kind carries a non-empty reason.
        INVARIANTS: Frozen, forbid-extra fields.
    AI-CORE-END

    Same flat shape as the wire's ``ResolveItemResult`` (``aoa-fastapi-adapter``), one
    layer deeper: no ``allowed``/``level`` pair that could disagree with each other (the
    bug this shape replaces — ``allowed=True`` with a non-null ``level`` was expressible
    before, meaningless, and eventually happened). ``to_wire()`` copies ``kind``/``reason``
    straight across, no recomputation.

    The only validated contract is the one line in CONTRACT above — ``kind == SUCCESS``
    iff ``reason == ""`` — and nothing else about ``kind``/``reason`` is or should be
    checked here. In particular: today, no code path constructs an ``AccessVerdict``
    with ``kind=CHECK_ERROR`` — the access-control cascade itself never produces that
    channel, only the resolver does, around a check that was never reached at all (see
    :class:`ResolveItemKind`) — but that is a fact about today's call sites, not a rule
    this class enforces. Do not add a second, narrower validator for it or any other
    ``kind`` (fix-audit finding 6): a client only ever needs to know success-vs-not and
    the reason string: no combination of `kind`/`reason` should be validated beyond it.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    action: type[BaseAction]  # type: ignore[type-arg]  # pydantic rejects a parametrized type[X[...]] here
    kind: ResolveItemKind
    reason: str

    @model_validator(mode="after")
    def _reason_matches_kind(self) -> Self:
        """Enforce the CONTRACT line above in code, not only in the docstring.

        Second line of defense, not the primary fix: ``grant()``/``check_roles()``
        already reject an empty ``reason=`` at declaration time (see their own
        ``ValueError``s), so a well-formed cascade never reaches this validator with
        a mismatch. This catches anything that builds an ``AccessVerdict`` some other
        way — by hand, or from a future denial source that forgets to set ``reason``.
        """
        if (self.kind == ResolveItemKind.SUCCESS) != (self.reason == ""):
            raise ValueError(
                "AccessVerdict: kind=SUCCESS must carry reason=''; every other kind must "
                f"carry a non-empty reason — got kind={self.kind!r}, reason={self.reason!r}."
            )
        return self
