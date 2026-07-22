# packages/aoa-action-machine/src/aoa/action_machine/intents/access_control/access_verdict.py
"""BaseVerdict — every access-check outcome, one class per outcome, no shared kind/reason flag."""

from __future__ import annotations

from typing import Any

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

    Replaces the old ``ResolveItemResult``/``AccessVerdict`` pair (one concrete type,
    a ``ResolveItemKind`` ``StrEnum`` field, and a validator enforcing
    ``kind == SUCCESS`` iff ``reason == ""``) with a type per outcome instead of a
    flag per outcome. ``kind`` is not a free field a caller could set to a wrong or
    mismatched value: ``__init__`` (below) fills it in from ``type(self).__name__``
    when omitted, and raises ``ValueError`` if a caller passes a ``kind=`` that
    disagrees with the class actually being constructed — the same guarantee a
    ``@computed_field`` would give, just enforced once, in one place, rather than
    inherited implicitly. (An earlier version of this class used a ``@computed_field``
    instead of a stored field — that gave a stronger, unconditional guarantee, at the
    cost of ``kind`` silently vanishing from ``BaseSchema``'s dict-like interface
    (``.keys()``/``.items()``/``in``, which only look at *declared* fields) and being
    unrecoverable from ``model_dump()`` output via ``model_validate()`` — a computed
    field is never accepted back as input. Both were real, reproduced bugs
    (baseverdict-audit findings 6 and 4, third document); a stored field closes both
    at once, deliberately trading the unconditional guarantee below for it.) Whether a
    given ``kind``/``reason`` combination is legal is therefore not something any
    validator checks: it is not expressible in the first place — you cannot construct
    a ``FailSecurityVerdict`` with an empty ``reason``, because that class simply has
    no way to represent "success", and you cannot construct an ``AllowedVerdict`` with
    a ``reason`` at all, because that class has no such field. Adding a new outcome is
    adding a new subclass, not editing a central enum — the old ``ResolveItemKind`` is
    gone entirely.

    This guarantee, and the "cannot construct" one two sentences up, both hold for the
    normal constructor. ``model_construct()`` and ``model_copy(update=...)`` are
    pydantic's own documented escape hatches for building an instance from
    already-trusted data without running validators — or ``__init__`` — at all
    (confirmed empirically): both can still produce e.g.
    ``FailSecurityVerdict(reason="")``, bypassing ``Field(min_length=1)`` and even
    ``frozen=True``, and, now that ``kind`` is a stored field rather than always
    ``type(self).__name__`` live, both can also produce a ``FailSecurityVerdict``
    instance whose ``kind`` claims to be ``"AllowedVerdict"`` — a lie the earlier
    computed-field design made structurally impossible even through these bypasses.
    Nothing in this codebase calls either method on a ``BaseVerdict``; if that ever
    changes, neither claim above holds for that call site (baseverdict-audit finding
    5, third document — this paragraph is that finding's resolution, extended to
    cover ``kind`` spoofing as a consequence of closing findings 4/6).

    Abstract by construction, not by convention: raises ``TypeError`` if
    ``type(self) is BaseVerdict``, checked in both ``__init__`` (the normal
    construction path) and ``model_post_init`` (which pydantic also calls from
    ``model_construct()``, the one construction path that skips ``__init__``
    entirely) — ``pydantic.BaseModel`` combined with ``abc.ABC`` alone does not block
    direct instantiation (confirmed empirically).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    # Field(default=...) exists only so mypy's pydantic plugin treats `kind` as
    # optional in the synthesized constructor it infers for subclasses that don't
    # define their own `__init__` (AllowedVerdict, e.g. `AllowedVerdict()` at every
    # existing call site) -- the default itself is never actually used at runtime,
    # __init__ below always supplies a real value explicitly.
    kind: str = Field(default="")

    def __init__(self, **kwargs: Any) -> None:
        expected_kind = type(self).__name__
        given_kind = kwargs.pop("kind", expected_kind)
        if given_kind != expected_kind:
            raise ValueError(
                f"kind must be {expected_kind!r} for {expected_kind} (it is derived from the "
                f"class being constructed, not a free field) -- got {given_kind!r}."
            )
        # mypy resolves super().__init__() against BaseSchema's own declared fields
        # (it has none) -- it does not see `kind`, declared here on this class, not
        # on the parent `super()` refers to. Pydantic's real, generated constructor
        # validates against type(self)'s full field set regardless of which class in
        # the MRO the call goes through (confirmed empirically), so this is a
        # static-analysis gap, not a runtime one.
        super().__init__(kind=expected_kind, **kwargs)  # type: ignore[call-arg]

    # pydantic.BaseModel.model_post_init is (self, context, /) -> None; pylint has no
    # pydantic-aware stub and infers a 0-arg signature for the hook, so this reads as a
    # mismatch even though it matches the real base method exactly.
    # pylint: disable-next=arguments-differ
    def model_post_init(self, __context: Any) -> None:
        if type(self) is BaseVerdict:  # pylint: disable=unidiomatic-typecheck
            # isinstance() would also match every subclass, defeating this guard --
            # only literal BaseVerdict itself is abstract, not "anything derived from it".
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
    why is not a state the normal constructor can represent (see ``BaseVerdict``'s
    own docstring for the ``model_construct``/``model_copy`` caveat to that claim).

    Subclasses may add their own fields — a subclass that does not override
    ``__init__`` still gets the positional ``reason`` for free, since ``**kwargs``
    here passes any of the subclass's own fields straight through to
    ``BaseVerdict.__init__``, which fills in ``kind`` from ``type(self).__name__``.

    Constructible positionally — ``FailSecurityVerdict("FORBIDDEN_ROLE")`` — since
    every call site in this codebase constructs one from a single reason string.
    ``reason`` is not positional-*only*: pydantic's own ``model_validate()``/
    ``model_validate_json()`` call ``__init__`` with keyword arguments internally,
    so a positional-only parameter would break deserialization (confirmed
    empirically) — ``FailSecurityVerdict(reason="...")`` works too.
    """

    reason: str = Field(min_length=1)

    def __init__(self, reason: str, **kwargs: Any) -> None:
        super().__init__(reason=reason, **kwargs)


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
        super().__init__(reason=reason, **kwargs)
