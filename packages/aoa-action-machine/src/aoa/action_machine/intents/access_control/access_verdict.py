# packages/aoa-action-machine/src/aoa/action_machine/intents/access_control/access_verdict.py
"""ResolveItemResult/AccessVerdict — one resolve answer, and the access-check result it is built from."""

from __future__ import annotations

from enum import StrEnum
from typing import Self

from pydantic import ConfigDict, Field, model_validator

from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.model.base_schema import BaseSchema


class ResolveItemKind(StrEnum):
    """
    Source channel a resolve answer came through — not a stability/severity ranking.

    Canonical home for this enum: it is what an access check actually decides, one
    layer below the wire (``ResolveItemResult`` below reuses it, never redefines
    it — and ``aoa-fastapi-adapter`` imports ``ResolveItemResult`` from here rather
    than declaring its own). ``SUCCESS``/``SECURITY``/``FLAG``/``MACHINE_RULE`` are
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


def kind_matches_reason(kind: ResolveItemKind, reason: str) -> bool:
    """The one contract validated on ``ResolveItemResult`` and everything that
    extends it (``AccessVerdict`` below): ``kind == SUCCESS`` iff ``reason == ""``.
    A free function, not a method, so a client written in another language
    (``aoa-client-js``'s ``kindMatchesReason``, chapter 4 of the book) can
    implement the identical rule without importing Python — nothing beyond this
    one line should ever be validated about ``kind``/``reason``, on any type,
    in any language (fix-audit findings 6 and 7).
    """
    return (kind == ResolveItemKind.SUCCESS) == (reason == "")


class ResolveItemResult(BaseSchema):
    """
    AI-CORE-BEGIN
        ROLE: One resolve answer — the shape that actually goes out over the wire.
        CONTRACT: kind=SUCCESS implies reason=""; every other kind carries a non-empty reason.
        INVARIANTS: Forbid-extra fields.
    AI-CORE-END

    Canonical home for the flat ``{kind, reason}`` shape: no ``allowed``/``level`` pair
    that could disagree with each other (the bug this shape replaces — ``allowed=True``
    with a non-null ``level`` was expressible before, meaningless, and eventually
    happened). Lives here, in ``aoa-action-machine``, rather than in ``aoa-fastapi-adapter``
    (which imports it), because both HTTP and MCP adapters depend on this package and
    neither should depend on the other's wire format — this is the one place both can see.

    ``AccessVerdict`` below *is* a ``ResolveItemResult`` (subclass, not a sibling type
    copied by ``to_wire()``): it adds exactly one field, ``action``, needed only inside
    the cascade, excluded from serialization. The two functions that build a
    ``ResolveItemResult`` with no real action behind it at all — an unknown operation,
    or a route-level auth rejection before the action ever resolved (``aoa-fastapi-adapter``,
    ``permissions.py``) — construct this base class directly; they were never going to
    have an ``action`` to give it, so ``action`` staying off the base class is not a
    workaround, it is the actual shape of those two cases.

    The only validated contract is the one line in CONTRACT above — ``kind == SUCCESS``
    iff ``reason == ""`` — and nothing else about ``kind``/``reason`` is or should be
    checked here or on any subclass (fix-audit finding 6): a client only ever needs to
    know success-vs-not and the reason string.
    """

    model_config = ConfigDict(extra="forbid")

    kind: ResolveItemKind
    reason: str

    @model_validator(mode="after")
    def _reason_matches_kind(self) -> Self:
        """Enforce the CONTRACT line above in code, not only in the docstring.

        Inherited automatically by every subclass (``AccessVerdict``) — not
        redeclared there, so there is exactly one place this rule is written
        (fix-audit finding 7). Second line of defense, not the primary fix:
        ``grant()``/``check_roles()`` already reject an empty ``reason=`` at
        declaration time (see their own ``ValueError``s), so a well-formed
        cascade never reaches this validator with a mismatch. This catches
        anything that builds a verdict some other way — by hand, or from a
        future denial source that forgets to set ``reason``.
        """
        if not kind_matches_reason(self.kind, self.reason):
            raise ValueError(
                f"{type(self).__name__}: kind=SUCCESS must carry reason=''; every other "
                f"kind must carry a non-empty reason — got kind={self.kind!r}, reason={self.reason!r}."
            )
        return self


class AccessVerdict(ResolveItemResult):
    """
    AI-CORE-BEGIN
        ROLE: Answer "can this run?" without executing the action — ResolveItemResult
              plus the one field only the cascade itself needs.
        INVARIANTS: Frozen (in addition to ResolveItemResult's forbid-extra).
    AI-CORE-END

    ``action`` is excluded from serialization (``Field(exclude=True)``): it is a live
    Python class reference, meaningful only inside this process, and every
    ``model_dump()``/``model_dump_json()`` — including the one FastAPI runs to answer
    ``POST /permissions/resolve`` — drops it regardless of the field's declared type on
    whatever container holds this instance. Nothing today actually reads ``.action``
    back off a verdict (checked by grep across both packages) — it exists for callers
    that might want it later (logging, tests) without forcing a resolver rewrite to add it.
    """

    model_config = ConfigDict(frozen=True)

    action: type[BaseAction] = Field(exclude=True)  # type: ignore[type-arg]  # pydantic rejects a parametrized type[X[...]] here
