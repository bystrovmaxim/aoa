# packages/aoa-action-machine/src/aoa/action_machine/runtime/include_contract_checker.py
"""
``IncludeContractChecker`` — validates ``UseCase.include`` after a successful root run.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

After the action pipeline completes without an unhandled exception, the machine
checks that every ``@depends(..., mode=UseCase.include)`` on the **root** action
was satisfied: each required action type must have been entered at least once
via ``_run_internal`` during that root execution (including nested ``box.run`` /
``machine.run``). ``UseCase.extend`` and resource dependencies are ignored here.

**Interaction with** ``@on_error``: when the pipeline returns a ``Result`` produced
only by an error handler, the run is still considered successful from the
machine's perspective; include verification runs in that case as well (PR-4).

**Cache hits (root):** the machine skips this check when the root run is served
from the action cache without executing the aspect pipeline, because nested
``_run_internal`` calls from a prior materialization are not part of this
``ContextVar`` session (PR-4 / PR-0 cache policy).
"""

from __future__ import annotations

from typing import TypeVar

from aoa.action_machine.exceptions.include_contract_violation_error import IncludeContractViolationError
from aoa.action_machine.intents.depends.depends_intent_resolver import DependsIntentResolver
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.base_result import BaseResult

P = TypeVar("P", bound=BaseParams)
R = TypeVar("R", bound=BaseResult)


class IncludeContractChecker:
    """
    AI-CORE-BEGIN
    ROLE: Post-condition for ``UseCase.include`` on a completed root action run.
    CONTRACT: ``verify`` is a no-op when there are no include-only dependencies.
    INVARIANTS: Uses declaration order from ``DependsIntentResolver``; ``called_types`` is authoritative for the current root session.
    AI-CORE-END
    """

    @staticmethod
    def verify(parent_action: BaseAction[P, R], called_types: frozenset[type]) -> None:
        """
        Raise :exc:`IncludeContractViolationError` if an ``include`` dependency type
        was never observed in ``called_types``.
        """
        include_types = DependsIntentResolver.resolve_include_dependency_types(type(parent_action))
        if not include_types:
            return
        missing = frozenset(t for t in include_types if t not in called_types)
        if not missing:
            return
        missing_sorted = sorted(missing, key=lambda c: c.__qualname__)
        names = ", ".join(c.__qualname__ for c in missing_sorted)
        raise IncludeContractViolationError(
            f"{type(parent_action).__name__}: UseCase.include dependencies were not executed "
            f"via _run_internal in this root run: {names}",
            missing_include_types=missing,
        )
