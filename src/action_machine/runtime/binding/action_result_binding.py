# src/action_machine/runtime/binding/action_result_binding.py
"""
Runtime binding of pipeline outputs to declared ``BaseAction[P, R]`` result type.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Enforces result-type contracts at runtime. Resolves declared ``R`` from
``BaseAction[P, R]``, synthesizes fallback result when allowed, and validates
pipeline output instances before returning them to callers.
"""

from __future__ import annotations

from typing import cast

from action_machine.exceptions import (
    ActionResultDeclarationError,
    ActionResultTypeError,
    MissingSummaryAspectError,
)
from action_machine.model.base_result import BaseResult
from action_machine.model.result_stub import ResultStub
from action_machine.runtime.binding.extract_action_params_result_types import (
    extract_action_params_result_types,
)


def require_resolved_action_result_type(action_cls: type) -> type:
    """
    Return the declared ``R`` from ``BaseAction[P, R]`` or raise ``TypeError``.

    ``R`` must be a ``BaseResult`` subclass.
    """
    _, r_type = extract_action_params_result_types(action_cls)
    if r_type is None:
        raise ActionResultDeclarationError(
            f"{action_cls.__name__}: cannot resolve Result type from BaseAction[P, R]. "
            "Declare BaseAction[Params, Result] with concrete or resolvable forward refs."
        )
    if not issubclass(r_type, BaseResult):
        raise ActionResultDeclarationError(
            f"{action_cls.__name__}: declared Result type {r_type.__name__!r} "
            "must be a subclass of BaseResult."
        )
    return r_type


def synthetic_summary_result_when_missing_aspect(action_cls: type) -> BaseResult:
    """
    Result used when the action has no ``@summary_aspect``.

    Synthesis is allowed only for the non-graph roots used as placeholders:
    exact :class:`~action_machine.model.base_result.BaseResult` (empty model) or
    :class:`~action_machine.model.result_stub.ResultStub` (default ``ok=True``).
    Any other declared ``R`` subtype still requires a ``@summary_aspect``.
    """
    r_type = require_resolved_action_result_type(action_cls)
    if r_type is BaseResult:
        return BaseResult()
    if r_type is ResultStub:
        return ResultStub()
    raise MissingSummaryAspectError(
        f"{action_cls.__name__} declares Result type {r_type.__name__} but has no "
        "@summary_aspect; add a summary method or bind ``R`` to ``BaseResult`` or "
        "``ResultStub`` when a synthetic placeholder outcome is acceptable."
    )


def bind_pipeline_result_to_action(
    action_cls: type,
    result: object,
    *,
    source: str,
) -> BaseResult:
    """Ensure ``result`` is an instance of the action's declared ``R``."""
    r_type = require_resolved_action_result_type(action_cls)
    if not isinstance(result, r_type):
        raise ActionResultTypeError(
            f"{action_cls.__name__}: {source} must return an instance of "
            f"{r_type.__name__}, got {type(result).__name__!r}.",
            expected_type=r_type,
            actual_type=type(result),
        )
    return cast(BaseResult, result)
