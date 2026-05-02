# src/action_machine/runtime/binding/__init__.py
"""
Runtime binding helpers for ``BaseAction[P, R]`` generics — P/R extraction and result checks.
"""

from __future__ import annotations

from action_machine.runtime.binding.action_generic_params import (
    _resolve_forward_ref,
    _resolve_generic_arg,
)
from action_machine.runtime.binding.action_result_binding import (
    bind_pipeline_result_to_action,
    require_resolved_action_result_type,
    synthetic_summary_result_when_missing_aspect,
)
from action_machine.runtime.binding.extract_action_params_result_types import (
    extract_action_params_result_types,
)

__all__ = [
    "_resolve_forward_ref",
    "_resolve_generic_arg",
    "bind_pipeline_result_to_action",
    "extract_action_params_result_types",
    "require_resolved_action_result_type",
    "synthetic_summary_result_when_missing_aspect",
]
