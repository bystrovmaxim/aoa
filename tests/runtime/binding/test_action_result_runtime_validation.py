# tests/runtime/binding/test_action_result_runtime_validation.py
"""Unit checks for ``action_result_binding`` helpers and synthetic summary."""

from __future__ import annotations

import pytest

from action_machine.exceptions import (
    ActionResultDeclarationError,
    MissingSummaryAspectError,
)
from action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from action_machine.intents.check_roles import NoneRole, check_roles
from action_machine.intents.meta.meta_decorator import meta
from action_machine.model.base_action import BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from action_machine.model.base_state import BaseState
from action_machine.model.params_stub import ParamsStub
from action_machine.model.result_stub import ResultStub
from action_machine.resources.base_resource import BaseResource
from action_machine.runtime.binding.action_result_binding import (
    bind_pipeline_result_to_action,
    require_resolved_action_result_type,
    synthetic_summary_result_when_missing_aspect,
)
from action_machine.runtime.tools_box import ToolsBox
from tests.scenarios.domain_model.domains import TestDomain


class _P(BaseParams):
    pass


class _R(BaseResult):
    ok: bool = True


def test_require_resolved_action_result_type_raises_on_plain_class() -> None:
    class _Plain:
        pass

    with pytest.raises(ActionResultDeclarationError, match="cannot resolve Result type"):
        require_resolved_action_result_type(_Plain)


def test_bind_pipeline_result_raises_declaration_error_when_r_unresolved() -> None:
    class _Plain:
        pass

    with pytest.raises(ActionResultDeclarationError):
        bind_pipeline_result_to_action(_Plain, BaseResult(), source="unit")


def test_bind_pipeline_result_accepts_instance_of_declared_r() -> None:
    @meta(description="probe", domain=TestDomain)
    @check_roles(NoneRole)
    class _ProbeAction(BaseAction[_P, _R]):
        @summary_aspect("s")
        async def probe_summary(
            self,
            params: _P,
            state: BaseState,
            box: ToolsBox,
            connections: dict[str, BaseResource],
        ) -> _R:
            return _R()

    out = bind_pipeline_result_to_action(
        _ProbeAction,
        _R(ok=True),
        source="unit",
    )
    assert isinstance(out, _R)
    assert out.ok is True


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
