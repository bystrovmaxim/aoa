# packages/aoa-action-machine/src/aoa/action_machine/intents/access_control/access_verdict.py
"""BaseVerdict — every access-check outcome, one class per outcome, no shared kind/reason flag."""

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

    One class per outcome, not one class with a flag: an illegal ``kind``/``reason``
    combination is not rejected by a validator, it is unrepresentable. ``AllowedVerdict``
    has no ``reason`` field at all; ``FailSecurityVerdict``/``FailErrorVerdict`` cannot
    carry an empty one. A new outcome is a new subclass, not an edit to a central enum.

    Bypasses that do exist, each pinned by a test in ``test_access_verdict.py``:
    ``model_construct()``/``model_copy(update=...)`` skip validation and ``frozen=True``
    but return a *new* object; ``object.__setattr__`` and ``__dict__`` assignment write
    into the instance itself, which for the shared ``FORBIDDEN_OBJECT`` below poisons
    every later denial in the process. ``Final`` is an annotation, not a runtime lock.
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
        # the MRO the call goes through, so this is a static-analysis gap, not a
        # runtime one.
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
    so a positional-only parameter would break deserialization —
    ``FailSecurityVerdict(reason="...")`` works too.
    """

    reason: str = Field(min_length=1)

    def __init__(self, reason: str, **kwargs: Any) -> None:
        super().__init__(reason=reason, **kwargs)


# Shared, reusable denial for "no such object" and "object belongs to someone
# else" in an access_decide() implementation. Both cases must answer with this
# exact same instance, not two separate FailSecurityVerdict("...") calls with
# different text -- otherwise the reason string itself becomes an oracle for
# which object IDs exist. See CancelOrderAction.access_decide (aoa-demo) for a
# real usage.
#
# Check existence and ownership in ONE branch, not two steps. Writing
#
#     if order is None:            return FORBIDDEN_OBJECT   # step 1
#     if order.owner != caller:    return FORBIDDEN_OBJECT   # step 2
#
# returns the same verdict today and is still the wrong shape, for two reasons:
#
#   * Two branches drift. They are edited at different times for different
#     reasons, and the moment someone makes one of them more specific -- which
#     reads like a harmless improvement, since ownership is not in question on
#     the "missing" path -- the pair stops being indistinguishable. One combined
#     condition cannot drift apart from itself.
#   * Two branches take measurably different work. Step 1 returns without ever
#     touching the ownership comparison (and, in a real action, often without
#     the extra lookup that comparison needs), so "missing" answers sooner than
#     "foreign" -- the same oracle, read off the clock instead of the text.
#
# Once ownership *is* confirmed, a more specific reason is safe: the caller has
# proven the object is theirs, so a precise message tells them nothing about
# anyone else's.
FORBIDDEN_OBJECT: Final = FailSecurityVerdict("FORBIDDEN_OBJECT")


class FailErrorVerdict(BaseVerdict):
    """
    The check itself could not be answered — not a denial, and must never be cached
    as one. Two sources: a structural "couldn't even route the question" (e.g.
    ``UNKNOWN_ENDPOINT`` — ``aoa-fastapi-adapter``, ``permissions.py``, an operation
    that never resolves to an action at all), or a genuinely unexpected exception
    anywhere in the check path (``reason`` = the fixed ``"EVALUATION_FAILED"`` —
    see ``ActionProductMachine.check_access_decide``, not the exception's own
    type or message, for the same reason ``FORBIDDEN_OBJECT`` is one fixed value
    rather than free text: a distinguishable failure reason is itself a probing
    surface). Distinct from ``FailSecurityVerdict`` on purpose: "we don't know" and
    "no" must stay distinguishable, or a transient failure (a database hiccup
    during ``access_decide()``) gets cached as a permanent, incorrect "no".

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
