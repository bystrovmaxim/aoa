# tests/runtime/binding/test_action_result_runtime_validation.py
"""Unit checks for ``action_result_binding`` helpers and synthetic summary."""

from __future__ import annotations

import pytest

from action_machine.exceptions import MissingSummaryAspectError
from action_machine.intents.action_schema.action_schema_intent_resolver import (
    ActionSchemaIntentResolver,
)
from action_machine.intents.check_roles import NoneRole, check_roles
from action_machine.intents.meta.meta_decorator import meta
from action_machine.model.base_action import BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from action_machine.model.params_stub import ParamsStub
from action_machine.model.result_stub import ResultStub
from action_machine.runtime.binding.action_result_binding import (
    synthetic_summary_result_when_missing_aspect,
)
from tests.scenarios.domain_model.domains import TestDomain


class _P(BaseParams):
    pass


class _R(BaseResult):
    ok: bool = True


def test_resolve_result_type_plain_class_raises_value_error() -> None:
    class _Plain:
        pass

    with pytest.raises(ValueError, match="Failed to resolve result type"):
        ActionSchemaIntentResolver.resolve_result_type(_Plain)


# Module-level: pytest's assertion rewriter can corrupt ``BaseAction[P, R]`` subscripts
# inside some sync tests that also contain heavy ``assert`` rewrites.
@meta(description="synthetic probe", domain=TestDomain)
@check_roles(NoneRole)
class _SyntheticSummaryProbeAction(BaseAction[ParamsStub, ResultStub]):
    pass


def test_synthetic_summary_when_missing_aspect_base_result_only() -> None:
    """Use module-level action class: nested ``BaseAction[P, R]`` under pytest assert rewrite can break ``R``."""
    r = synthetic_summary_result_when_missing_aspect(_SyntheticSummaryProbeAction)
    assert type(r) is ResultStub
    assert r.ok is True


def test_synthetic_summary_when_missing_aspect_result_stub() -> None:
    r = synthetic_summary_result_when_missing_aspect(_SyntheticSummaryProbeAction)
    assert type(r) is ResultStub
    assert r.ok is True


def test_synthetic_summary_when_missing_aspect_custom_r_raises() -> None:
    @meta(description="no synth for custom R", domain=TestDomain)
    @check_roles(NoneRole)
    class _CustomRAction(BaseAction[_P, _R]):
        pass

    with pytest.raises(MissingSummaryAspectError, match="@summary_aspect"):
        synthetic_summary_result_when_missing_aspect(_CustomRAction)
