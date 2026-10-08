# packages/aoa-action-machine/src/aoa/action_machine/intents/access_control/cascade.py
"""
The access cascade — one decision, four ordered steps, three answers.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

One place answers "may this call proceed", and it answers it the same way whether
the call is about to run or someone is asking in advance. The rule is deliberately
small: the steps run in a fixed order, the first one that answers ends the
decision, and a step that cannot tell is an answer of its own — never a refusal.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    decide(context, action, params, box, connections)
        │
        ├─ auth_gate     who is calling          → AUTH_COORDINATOR
        ├─ roles_gate    the roles they hold,
        │                with each grant's own
        │                declared condition      → CHECK_ROLES, or WHEN when a matched
        │                                          role's condition is what refused
        ├─ guard_gate    the operation's shared
        │                declared condition      → GUARD
        └─ object_gate   the object of the call  → ACCESS_DECIDE
                │
                └─ first step that answers ends the decision; all passing answers Allowed

    A step that raises is turned into ``Undecided`` naming the gate it belongs to,
    with the failure kept as its cause. ``WHEN`` is answered *by* the roles step, so
    a failure of that step names ``CHECK_ROLES``: the word says which step could not
    tell, and the steps are four while the words are five.

    The cascade reads the same declarations the assembled graph carries — roles,
    conditions and the object check come from their intent resolvers, never from an
    inherited method — so it needs no access to the graph itself, and the graph stays
    the observable form of exactly these facts.

    Nothing is published here: the cascade decides, the machine publishes (FR-013,
    FR-014). Keeping the decision free of plugins is what makes it testable on its
    own and keeps one answer for both paths (FR-002).

═══════════════════════════════════════════════════════════════════════════════
SCOPE (IN / OUT)
═══════════════════════════════════════════════════════════════════════════════

IN: the order of the steps, the shape a step answers with, the three answers, and
turning a step's failure into "cannot tell".

OUT: emitting events, raising for the caller, judging what a transport does with
the answer, and deciding what each step considers — that belongs to the step.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aoa.action_machine.context.context import Context
from aoa.action_machine.intents.access_control.allowed import Allowed
from aoa.action_machine.intents.access_control.gate import Gate
from aoa.action_machine.intents.access_control.refused import Refused
from aoa.action_machine.intents.access_control.roles import RoleChecker
from aoa.action_machine.intents.access_control.undecided import Undecided
from aoa.action_machine.intents.access_control.verdict import Verdict
from aoa.action_machine.intents.access_decide.access_decide_intent_resolver import AccessDecideIntentResolver
from aoa.action_machine.intents.check_roles.check_roles_intent_resolver import CheckRolesIntentResolver
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.runtime.tools_box import ToolsBox

StepAnswer = Verdict | None
"""What a step answers: the decision, or ``None`` to let the next step decide."""

Step = Callable[
    [Context, BaseAction[Any, Any], BaseParams | None, ToolsBox, dict[str, BaseResource]],
    Awaitable[StepAnswer],
]
"""One ordered step of the decision: it answers, or it passes."""

GATES_BEFORE_RUN: tuple[Gate, ...] = (Gate.AUTH_COORDINATOR, Gate.CHECK_ROLES, Gate.GUARD)
"""The steps that decide whether a run exists at all — nothing is announced while they answer."""

GATES_AT_OBJECT: tuple[Gate, ...] = (Gate.ACCESS_DECIDE,)
"""The step that decides inside a run — the only one that runs once the run is under way."""

GATES: tuple[Gate, ...] = GATES_BEFORE_RUN + GATES_AT_OBJECT
"""Every step, in the order they run. The order is part of the contract, and so is the seam:
the run exists only between the two phases, which is why the machine asks for them separately."""


async def auth_gate(
    context: Context,
    action: BaseAction[Any, Any],
    params: BaseParams | None,
    box: ToolsBox,
    connections: dict[str, BaseResource],
) -> StepAnswer:
    """Answer for the credentials the caller presented; this step owns ``AUTH_COORDINATOR``.

    The engine never answers it, and that is deliberate: a transport that authenticates
    refuses before it asks for a decision, so by the time a context reaches the cascade
    there are no rejected credentials left to judge. The step keeps its place in the order
    and its word, so the vocabulary a caller reads stays complete and an engine-side
    identity check would have a home.
    """
    _ = (context, action, params, box, connections)
    return None


async def roles_gate(
    context: Context,
    action: BaseAction[Any, Any],
    params: BaseParams | None,
    box: ToolsBox,
    connections: dict[str, BaseResource],
) -> StepAnswer:
    """Answer for the roles the caller holds; this step owns ``CHECK_ROLES`` and ``WHEN``."""
    _ = (box, connections)
    return _ROLE_CHECKER.check(context, type(action), params)


def guard_answer(context: Context, action: BaseAction[Any, Any], params: BaseParams | None) -> Refused | None:
    """Answer for the operation's shared condition — the rule ``guard_gate`` carries."""
    guard = CheckRolesIntentResolver.resolve_guard(type(action))
    if guard is None or guard(context.user, params):
        return None
    return Refused(gate=Gate.GUARD)


async def guard_gate(
    context: Context,
    action: BaseAction[Any, Any],
    params: BaseParams | None,
    box: ToolsBox,
    connections: dict[str, BaseResource],
) -> StepAnswer:
    """Answer for the operation's shared condition; this step owns ``GUARD``."""
    _ = (box, connections)
    return guard_answer(context, action, params)


async def object_gate(
    context: Context,
    action: BaseAction[Any, Any],
    params: BaseParams | None,
    box: ToolsBox,
    connections: dict[str, BaseResource],
) -> StepAnswer:
    """Answer about the object of the call; an operation that declares no check passes.

    The check answers with one of the three answers and nothing else. Anything else — a
    ``bool``, a string, ``None``, an object of its own — is a mistake, not an answer: it
    cannot be read as "allowed", and the cascade turns the ``TypeError`` into an
    ``undecided`` answer naming this step, with the mistake kept as its cause. A check
    that fails is treated the same way, and neither is ever read as a refusal (FR-005).
    """
    declared = AccessDecideIntentResolver.resolve_check(type(action))
    if declared is None:
        return None

    answer = await declared(action, params, context, box, connections)
    if not isinstance(answer, Allowed | Refused | Undecided):
        raise TypeError(
            f"{type(action).__name__}.{declared.__name__} answered {answer!r} "
            f"({type(answer).__name__}); an object check answers Allowed, Refused or Undecided."
        )
    return answer


_ROLE_CHECKER = RoleChecker()
"""The role-matching engine, asked for an answer rather than a raise."""

_STEPS: dict[Gate, Step] = {
    Gate.AUTH_COORDINATOR: auth_gate,
    Gate.CHECK_ROLES: roles_gate,
    Gate.GUARD: guard_gate,
    Gate.ACCESS_DECIDE: object_gate,
}
"""The step that owns each word. A failing step names its own word, so ``WHEN`` has none."""


async def decide(
    context: Context,
    action: BaseAction[Any, Any],
    params: BaseParams | None,
    box: ToolsBox,
    connections: dict[str, BaseResource],
    gates: tuple[Gate, ...] = GATES,
) -> Verdict:
    """
    Return the decision for one call: the first answer a step gives, or ``Allowed``.

    A step that raises cannot tell, and that is an answer of its own — ``Undecided``
    naming the step's gate, carrying the failure as its cause (FR-005).

    ``gates`` selects the phase: :data:`GATES_BEFORE_RUN` answers whether a run may start
    (``Allowed`` means it may), :data:`GATES_AT_OBJECT` answers inside a run that is already
    under way. The machine asks for the two separately because only it knows when a run
    exists — and announcing one is not this function's business (FR-013).
    """
    for gate in gates:
        step = _STEPS[gate]
        try:
            answer = await step(context, action, params, box, connections)
        except Exception as exc:
            return Undecided(gate=gate, cause=exc)
        if answer is not None:
            return answer
    return Allowed()


__all__ = [
    "GATES",
    "GATES_AT_OBJECT",
    "GATES_BEFORE_RUN",
    "Step",
    "StepAnswer",
    "auth_gate",
    "decide",
    "guard_answer",
    "guard_gate",
    "object_gate",
    "roles_gate",
]
