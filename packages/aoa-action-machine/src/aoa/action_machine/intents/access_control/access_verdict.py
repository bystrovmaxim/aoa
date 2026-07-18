# packages/aoa-action-machine/src/aoa/action_machine/intents/access_control/access_verdict.py
"""AccessVerdict — result of an access check without executing the action."""

from __future__ import annotations

from enum import StrEnum

from pydantic import ConfigDict

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
    straight across, no recomputation. ``CHECK_ERROR`` never appears on an ``AccessVerdict``
    instance — see :class:`ResolveItemKind`.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    action: type[BaseAction]  # type: ignore[type-arg]  # pydantic rejects a parametrized type[X[...]] here
    kind: ResolveItemKind
    reason: str
