# packages/aoa-action-machine/src/aoa/action_machine/intents/check_roles/reason_validation.py
"""Shared ``reason=`` companion-validation for ``grant(when=...)`` and ``check_roles(guard=...)``."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Deferred: access_control transitively imports nearly the whole package (via
    # model.base_schema); this module sits inside that same transitive chain (loaded
    # by intents/check_roles/__init__.py via grant.py/check_roles_decorator.py), so a
    # top-level import would cycle depending on which module happens to be imported
    # first. The one runtime construction (the default FailSecurityVerdict below)
    # imports locally instead.
    from aoa.action_machine.intents.access_control import FailSecurityVerdict


def require_reason_alongside(
    condition: object | None,
    reason: FailSecurityVerdict | None,
    *,
    condition_name: str,
    context: str,
    default_reason: str,
) -> FailSecurityVerdict | None:
    """
    Enforce ``reason=``'s type and its pairing with its condition (``when=``/``guard=``), and default it.

    ``reason=`` must actually be a ``FailSecurityVerdict`` (subclasses included) when given —
    the parameter is typed that way, but Python does not enforce annotations at runtime, and
    ``reason`` was a plain ``str`` before the ``BaseVerdict`` redesign, so a caller migrating
    old code (or simply not running mypy over the call site) can otherwise pass an ordinary
    string through unnoticed. That string then reaches ``AuthorizationError.verdict`` and
    crashes the first time something reads ``.verdict.reason`` off it — in production, at the
    exact moment a real denial needs to explain itself (baseverdict-audit finding 3, third
    document).

    ``reason=`` without the condition is meaningless — nothing can reject, so there is
    nothing to explain. The condition without ``reason=`` defaults to a framework-owned
    ``FailSecurityVerdict(default_reason)``, so a developer who doesn't care to write a
    specific reason gets a generic one instead of being forced to invent one (fix-audit
    finding 15, second document: this was the same check, written twice, once for
    ``grant()``'s ``when=`` and once for ``check_roles()``'s ``guard=``, differing only
    in these names and the default string).

    Raises:
        TypeError: ``reason`` was given but is not a ``FailSecurityVerdict``.
        ValueError: ``reason`` was given without ``condition``.
    """
    # pylint: disable-next=import-outside-toplevel
    from aoa.action_machine.intents.access_control import FailSecurityVerdict  # see TYPE_CHECKING note above

    if reason is not None and not isinstance(reason, FailSecurityVerdict):
        raise TypeError(f"{context}: reason= must be a FailSecurityVerdict instance, got {type(reason).__name__}.")
    if reason is not None and condition is None:
        raise ValueError(
            f"{context}: reason= was given without {condition_name}= — there is no condition for it to explain."
        )
    if condition is not None and reason is None:
        return FailSecurityVerdict(default_reason)
    return reason
