# packages/aoa-action-machine/src/aoa/action_machine/intents/check_roles/reason_validation.py
"""
The rules a declared reason lives by — checked where it is declared.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A reason explains a condition, and it is the developer's text: the framework invents
none of its own (FR-010, FR-012). A condition and its reason are declared together —
one without the other is a mistake, and all of them are refused while the capability is
declared rather than while a caller is being judged:

- a condition with no reason — the caller would have to guess why the operation refused,
  which is exactly what the answer is for;
- a reason with nothing to explain — there is no rule whose refusal it could describe,
  so the text would never reach anyone;
- a blank or non-textual reason — an answer refuses to carry one (`Refused` requires
  text), so saying so at declaration time beats a surprise at the first refusal.

═══════════════════════════════════════════════════════════════════════════════
SCOPE (IN / OUT)
═══════════════════════════════════════════════════════════════════════════════

IN: the pairing of a reason with its condition, and what counts as usable text.

OUT: where the reason is stored, how it reaches the graph, and what a step does with
it — each of those belongs to the declaration and the step that carries it.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


def require_reason_alongside(
    condition: Callable[..., Any] | None,
    reason: str | None,
    *,
    condition_name: str,
    reason_name: str,
) -> None:
    """
    Refuse a condition that does not explain itself, and a reason with nothing to explain.

    Args:
        condition: The declared condition the reason explains, or ``None``.
        reason: The declared reason, or ``None`` when the developer declared none — which is
            only valid together with no condition at all.
        condition_name: The parameter the condition came from, for the message.
        reason_name: The parameter the reason came from, for the message.

    Raises:
        TypeError: the reason is not text.
        ValueError: the reason has no condition to explain, or is blank.
    """
    if condition is None and reason is None:
        return
    if condition is None:
        raise ValueError(
            f"{reason_name} can only be declared beside a condition ({condition_name}=): "
            "a reason explains a refusal, and the framework invents none of its own."
        )
    if reason is None:
        raise ValueError(
            f"{condition_name}= must say why it refuses: declare {reason_name}= beside it, "
            "because a caller must not have to guess."
        )
    if not isinstance(reason, str):
        raise TypeError(f"{reason_name} must be a string, got {type(reason).__name__}.")
    if not reason.strip():
        raise ValueError(f"{reason_name} must be text a caller can read, not blank.")


__all__ = ["require_reason_alongside"]
