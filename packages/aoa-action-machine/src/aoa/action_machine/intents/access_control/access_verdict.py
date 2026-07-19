# packages/aoa-action-machine/src/aoa/action_machine/intents/access_control/access_verdict.py
"""BaseVerdict — every access-check outcome, one class per outcome, no shared kind/reason flag."""

from __future__ import annotations

from typing import Any

from pydantic import ConfigDict, Field, computed_field

from aoa.action_machine.model.base_schema import BaseSchema


class BaseVerdict(BaseSchema):
    """
    AI-CORE-BEGIN
        ROLE: Abstract root of every access-check outcome — the shape that goes out
              over the wire, one flat class per outcome.
        CONTRACT: kind is always exactly type(self).__name__; cannot be instantiated directly.
        INVARIANTS: Forbid-extra fields, frozen.
    AI-CORE-END

    Replaces the old ``ResolveItemResult``/``AccessVerdict`` pair (one concrete type,
    a ``ResolveItemKind`` ``StrEnum`` field, and a validator enforcing
    ``kind == SUCCESS`` iff ``reason == ""``) with a type per outcome instead of a
    flag per outcome. ``kind`` is not a free field a caller could set to a wrong or
    mismatched value — it is a ``@computed_field`` returning ``type(self).__name__``,
    defined once, here, and inherited by every subclass without redeclaration.
    Whether a given ``kind``/``reason`` combination is legal is therefore not
    something any validator checks: it is not expressible in the first place — you
    cannot construct a ``FailSecurityVerdict`` with an empty ``reason``, because that
    class simply has no way to represent "success", and you cannot construct an
    ``AllowedVerdict`` with a ``reason`` at all, because that class has no such field.
    Adding a new outcome is adding a new subclass, not editing a central enum — the
    old ``ResolveItemKind`` is gone entirely.

    Abstract by construction, not by convention: ``model_post_init`` raises
    ``TypeError`` if ``type(self) is BaseVerdict``. ``pydantic.BaseModel`` combined
    with ``abc.ABC`` alone does not block direct instantiation (confirmed
    empirically) — an abstract ``@computed_field`` property does, but would force
    every subclass to redeclare ``kind``, defeating the point of computing it once.
    A ``model_post_init`` guard is the narrowest fix that keeps ``kind`` inherited,
    not redeclared.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def kind(self) -> str:
        return type(self).__name__

    def model_post_init(self, __context: Any) -> None:
        if type(self) is BaseVerdict:
            raise TypeError(f"{type(self).__name__} is abstract and cannot be instantiated directly.")


class AllowedVerdict(BaseVerdict):
    """
    The one way to say "yes". Carries no ``reason`` field at all — not an empty one,
    none — there is nothing to explain when nothing rejected the call. This is also
    the only value ``BaseAction.access_decide()`` returns by default (see
    ``model/base_action.py``): unless an action overrides it, access is allowed.
    """


class FailSecurityVerdict(BaseVerdict):
    """
    A real access-control denial — the cascade looked at who is asking and said no.
    Every level of the cascade builds one of these: ``FORBIDDEN_ROLE`` (no role
    matched at all), ``FORBIDDEN_GRANT``/``FORBIDDEN_GUARD`` (a ``when=``/``guard=``
    condition rejected and the developer gave no ``reason=``), a developer-declared
    ``reason=`` on ``grant()``/``check_roles(guard=...)``, ``UNAUTHORIZED`` (a route's
    own auth check rejected the caller, ``aoa-fastapi-adapter``), or whatever
    ``access_decide()`` itself returns. ``reason`` is mandatory and non-empty
    (``Field(min_length=1)``) — a ``FailSecurityVerdict`` with nothing to say about
    why is not a state this class can represent.

    Subclasses may add their own fields (same pattern as ``BaseVerdict.kind``: no
    redeclaration needed, ``kind`` keeps resolving to the subclass's own name) — a
    subclass that does not override ``__init__`` still gets the positional
    ``reason`` for free, since ``**kwargs`` here passes any of the subclass's own
    fields straight through to pydantic's own constructor.

    Constructible positionally — ``FailSecurityVerdict("FORBIDDEN_ROLE")`` — since
    every call site in this codebase constructs one from a single reason string.
    ``reason`` is not positional-*only*: pydantic's own ``model_validate()``/
    ``model_validate_json()`` call ``__init__`` with keyword arguments internally,
    so a positional-only parameter would break deserialization (confirmed
    empirically) — ``FailSecurityVerdict(reason="...")`` works too.
    """

    reason: str = Field(min_length=1)

    def __init__(self, reason: str, **kwargs: Any) -> None:
        # mypy resolves super().__init__() against BaseVerdict's own declared fields
        # (just the computed `kind`) -- it does not see `reason`, declared only here
        # on the subclass. Pydantic's real, generated constructor does validate it
        # (confirmed empirically), so this is a static-analysis gap, not a runtime one.
        super().__init__(reason=reason, **kwargs)  # type: ignore[call-arg]


class FailErrorVerdict(BaseVerdict):
    """
    The check itself could not be answered — not a denial, and must never be cached
    as one. Two sources: a structural "couldn't even route the question" (e.g.
    ``UNKNOWN_ENDPOINT`` — ``aoa-fastapi-adapter``, ``permissions.py``, an operation
    that never resolves to an action at all), or a genuinely unexpected exception
    anywhere in the check path (``reason`` = ``type(exc).__name__``). Distinct from
    ``FailSecurityVerdict`` on purpose: "we don't know" and "no" must stay
    distinguishable, or a transient failure (a database hiccup during
    ``access_decide()``) gets cached as a permanent, incorrect "no".

    This classification only affects what a *check-only* caller
    (``machine.check_access_decide()``, the resolver) reports and caches. On the real
    execution path (``machine.run()``), any outcome other than ``AllowedVerdict`` —
    including a crash that becomes a ``FailErrorVerdict`` here — still blocks the
    action from running; that guarantee comes from ordinary exception propagation,
    not from this class.
    """

    reason: str = Field(min_length=1)

    def __init__(self, reason: str, **kwargs: Any) -> None:
        # mypy resolves super().__init__() against BaseVerdict's own declared fields
        # (just the computed `kind`) -- it does not see `reason`, declared only here
        # on the subclass. Pydantic's real, generated constructor does validate it
        # (confirmed empirically), so this is a static-analysis gap, not a runtime one.
        super().__init__(reason=reason, **kwargs)  # type: ignore[call-arg]
