# packages/aoa-action-machine/src/aoa/action_machine/intents/check_roles/reason_validation.py
"""Shared ``reason=`` companion-validation for ``grant(when=...)`` and ``check_roles(guard=...)``."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Deferred: access_control pulls in most of the package, and that chain leads back
    # here, so importing it at the top raises ImportError.
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
    Pair ``reason=`` with its condition (``when=``/``guard=``), and supply one when missing.

    A condition with no reason gets a generic framework-owned one, so a developer who has
    nothing specific to say is not forced to invent something. A reason with no condition
    is refused: nothing can reject, so there is nothing to explain.

    The type is checked here rather than left to the annotation, because Python does not
    enforce annotations and a plain string would pass silently. It would then surface much
    later, at the moment a real denial tries to read its own reason.

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
