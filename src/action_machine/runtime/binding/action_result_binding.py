# src/action_machine/runtime/binding/action_result_binding.py
"""
Synthetic summary fallback when an action declares no ``@summary_aspect``.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Produce placeholder ``BaseResult`` / ``ResultStub`` outcomes when pipeline rules
allow synthesis instead of requiring a summary method.
"""

from __future__ import annotations

from action_machine.exceptions import MissingSummaryAspectError
from action_machine.intents.action_schema.action_schema_intent_resolver import (
    ActionSchemaIntentResolver,
)
from action_machine.model.base_result import BaseResult
from action_machine.model.result_stub import ResultStub


def synthetic_summary_result_when_missing_aspect(action_cls: type) -> BaseResult:
    """
    Result used when the action has no ``@summary_aspect``.

    Synthesis is allowed only for the non-graph roots used as placeholders:
    exact :class:`~action_machine.model.base_result.BaseResult` (empty model) or
    :class:`~action_machine.model.result_stub.ResultStub` (default ``ok=True``).
    Any other declared ``R`` subtype still requires a ``@summary_aspect``.
    """
    r_type = ActionSchemaIntentResolver.resolve_result_type(action_cls)
    if r_type is BaseResult:
        return BaseResult()
    if r_type is ResultStub:
        return ResultStub()
    raise MissingSummaryAspectError(
        f"{action_cls.__name__} declares Result type {r_type.__name__} but has no "
        "@summary_aspect; add a summary method or bind ``R`` to ``BaseResult`` or "
        "``ResultStub`` when a synthetic placeholder outcome is acceptable."
    )
