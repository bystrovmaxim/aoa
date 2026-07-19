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
    Enforce ``reason=``'s pairing with its condition (``when=``/``guard=``), and default it.

    ``reason=`` without the condition is meaningless — nothing can reject, so there is
    nothing to explain. The condition without ``reason=`` defaults to a framework-owned
    ``FailSecurityVerdict(default_reason)``, so a developer who doesn't care to write a
    specific reason gets a generic one instead of being forced to invent one (fix-audit
    finding 15, second document: this was the same check, written twice, once for
    ``grant()``'s ``when=`` and once for ``check_roles()``'s ``guard=``, differing only
    in these names and the default string).

    Raises:
        ValueError: ``reason`` was given without ``condition``.
    """
    if reason is not None and condition is None:
        raise ValueError(
            f"{context}: reason= was given without {condition_name}= — there is no condition for it to explain."
        )
    if condition is not None and reason is None:
        # pylint: disable-next=import-outside-toplevel
        from aoa.action_machine.intents.access_control import FailSecurityVerdict  # see TYPE_CHECKING note above

        return FailSecurityVerdict(default_reason)
    return reason
