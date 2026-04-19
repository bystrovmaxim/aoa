"""Runtime checks that summary and @on_error return the action's declared ``R``."""

from __future__ import annotations

import pytest

from action_machine.intents.aspects.regular_aspect_decorator import regular_aspect
from action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from action_machine.intents.check_roles import NoneRole, check_roles
from action_machine.intents.checkers import result_string
from action_machine.intents.compensate.compensate_decorator import compensate
from action_machine.context.context import Context
from action_machine.context.user_info import UserInfo
from action_machine.logging.log_coordinator import LogCoordinator
from action_machine.intents.meta.meta_decorator import meta
from action_machine.intents.on_error import on_error
from action_machine.model.base_action import BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from action_machine.model.base_state import BaseState
from action_machine.model.exceptions import (
    ActionResultDeclarationError,
    ActionResultTypeError,
    MissingSummaryAspectError,
)
from action_machine.resources.base_resource_manager import BaseResourceManager
from action_machine.runtime.binding.action_result_binding import (
    bind_pipeline_result_to_action,
    require_resolved_action_result_type,
    synthetic_summary_result_when_missing_aspect,
)
from action_machine.runtime.machines.action_product_machine import ActionProductMachine
from action_machine.runtime.tools_box import ToolsBox
from action_machine.testing import TestBench
from tests.scenarios.domain_model.domains import TestDomain


class _P(BaseParams):
    pass


class _R(BaseResult):
    ok: bool = True


class _WrongR(BaseResult):
    tag: str = "wrong"


@pytest.fixture()
def context() -> Context:
    return Context(user=UserInfo(user_id="u1", roles=()))


@pytest.mark.asyncio
async def test_summary_wrong_result_type_raises_action_result_type_error(
    context: Context,
) -> None:
    @meta(description="bad summary return", domain=TestDomain)
    @check_roles(NoneRole)
    class _BadSummaryAction(BaseAction[_P, _R]):
        @summary_aspect("x")
        async def build_bad_summary(
            self,
            params: _P,
            state: BaseState,
            box: ToolsBox,
            connections: dict[str, BaseResourceManager],
        ) -> _R:
            return _WrongR()  # type: ignore[return-value]

    machine = ActionProductMachine(
        mode="test",
        log_coordinator=LogCoordinator(loggers=[]),
    )
    with pytest.raises(ActionResultTypeError) as ei:
        await machine.run(context, _BadSummaryAction(), _P())
    assert ei.value.expected_type is _R
    assert ei.value.actual_type is _WrongR


@pytest.mark.asyncio
async def test_on_error_wrong_result_type_raises_action_result_type_error(
    bench: TestBench,
) -> None:
    @meta(description="bad on_error return", domain=TestDomain)
    @check_roles(NoneRole)
    class _BadOnErrorAction(BaseAction[_P, _R]):
        @regular_aspect("r")
        @result_string("x", required=True)
        async def r_aspect(
            self,
            params: _P,
            state: BaseState,
            box: ToolsBox,
            connections: dict[str, BaseResourceManager],
        ) -> dict[str, str]:
            raise ValueError("fail")

        @on_error(ValueError, description="h")
        async def handle_bad_on_error(
            self,
            params: _P,
            state: BaseState,
            box: ToolsBox,
            connections: dict[str, BaseResourceManager],
            error: Exception,
        ) -> _R:
            return _WrongR()  # type: ignore[return-value]

    with pytest.raises(ActionResultTypeError) as ei:
        await bench.run(_BadOnErrorAction(), _P(), rollup=False)
    assert ei.value.expected_type is _R
    assert ei.value.actual_type is _WrongR
    assert "handle_bad_on_error" in str(ei.value)
    assert "@on_error" in str(ei.value)


@pytest.mark.asyncio
async def test_no_summary_custom_result_type_raises_type_error(
    context: Context,
) -> None:
    @meta(description="no summary", domain=TestDomain)
    @check_roles(NoneRole)
    class _NoSummaryCustomRAction(BaseAction[_P, _R]):
        pass

    machine = ActionProductMachine(
        mode="test",
        log_coordinator=LogCoordinator(loggers=[]),
    )
    with pytest.raises(MissingSummaryAspectError, match="@summary_aspect"):
        await machine.run(context, _NoSummaryCustomRAction(), _P())


# ─────────────────────────────────────────────────────────────────────────────
# Happy paths
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_no_summary_base_result_action_returns_empty_base_result(
    context: Context,
) -> None:
    """Only ``BaseAction[..., BaseResult]`` may omit summary (synthetic empty result)."""

    @meta(description="no summary, base result only", domain=TestDomain)
    @check_roles(NoneRole)
    class _NoSummaryBaseResultAction(BaseAction[BaseParams, BaseResult]):
        pass

    machine = ActionProductMachine(
        mode="test",
        log_coordinator=LogCoordinator(loggers=[]),
    )
    result = await machine.run(context, _NoSummaryBaseResultAction(), BaseParams())
    assert type(result) is BaseResult


@pytest.mark.asyncio
async def test_summary_returns_declared_result_succeeds(context: Context) -> None:
    @meta(description="ok summary", domain=TestDomain)
    @check_roles(NoneRole)
    class _OkSummaryAction(BaseAction[_P, _R]):
        @summary_aspect("build")
        async def build_ok_summary(
            self,
            params: _P,
            state: BaseState,
            box: ToolsBox,
            connections: dict[str, BaseResourceManager],
        ) -> _R:
            return _R(ok=True)

    machine = ActionProductMachine(
        mode="test",
        log_coordinator=LogCoordinator(loggers=[]),
    )
    result = await machine.run(context, _OkSummaryAction(), _P())
    assert isinstance(result, _R)
    assert result.ok is True


@pytest.mark.asyncio
async def test_on_error_returns_declared_result_succeeds(bench: TestBench) -> None:
    @meta(description="ok on_error", domain=TestDomain)
    @check_roles(NoneRole)
    class _OkOnErrorAction(BaseAction[_P, _R]):
        @regular_aspect("r")
        @result_string("x", required=True)
        async def fail_aspect(
            self,
            params: _P,
            state: BaseState,
            box: ToolsBox,
            connections: dict[str, BaseResourceManager],
        ) -> dict[str, str]:
            raise ValueError("boom")

        @on_error(ValueError, description="recover")
        async def recover_on_error(
            self,
            params: _P,
            state: BaseState,
            box: ToolsBox,
            connections: dict[str, BaseResourceManager],
            error: Exception,
        ) -> _R:
            return _R(ok=False)

    result = await bench.run(_OkOnErrorAction(), _P(), rollup=False)
    assert isinstance(result, _R)
    assert result.ok is False


# ─────────────────────────────────────────────────────────────────────────────
# action_result_binding helpers (unit-level)
# ─────────────────────────────────────────────────────────────────────────────


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
            connections: dict[str, BaseResourceManager],
        ) -> _R:
            return _R()

    out = bind_pipeline_result_to_action(
        _ProbeAction,
        _R(ok=True),
        source="unit",
    )
    assert isinstance(out, _R)
    assert out.ok is True


def test_synthetic_summary_when_missing_aspect_base_result_only() -> None:
    @meta(description="synthetic probe", domain=TestDomain)
    @check_roles(NoneRole)
    class _SynthProbeAction(BaseAction[BaseParams, BaseResult]):
        pass

    r = synthetic_summary_result_when_missing_aspect(_SynthProbeAction)
    assert type(r) is BaseResult


def test_synthetic_summary_when_missing_aspect_custom_r_raises() -> None:
    @meta(description="no synth for custom R", domain=TestDomain)
    @check_roles(NoneRole)
    class _CustomRAction(BaseAction[_P, _R]):
        pass

    with pytest.raises(MissingSummaryAspectError, match="@summary_aspect"):
        synthetic_summary_result_when_missing_aspect(_CustomRAction)


@pytest.mark.asyncio
async def test_action_result_type_error_message_mentions_source() -> None:
    @meta(description="msg probe", domain=TestDomain)
    @check_roles(NoneRole)
    class _MsgAction(BaseAction[_P, _R]):
        @summary_aspect("named summary")
        async def named_summary(
            self,
            params: _P,
            state: BaseState,
            box: ToolsBox,
            connections: dict[str, BaseResourceManager],
        ) -> _R:
            return _WrongR()  # type: ignore[return-value]

    machine = ActionProductMachine(
        mode="test",
        log_coordinator=LogCoordinator(loggers=[]),
    )
    ctx = Context(user=UserInfo(user_id="u1", roles=()))
    with pytest.raises(ActionResultTypeError, match="named_summary") as ei:
        await machine.run(ctx, _MsgAction(), _P())
    assert "summary aspect" in str(ei.value).lower()


@pytest.mark.asyncio
async def test_forward_ref_action_wrong_summary_type_raises(bench: TestBench) -> None:
    """Same runtime check when generics use string forward refs (nested Result)."""

    @meta(description="fwd ref wrong return", domain=TestDomain)
    @check_roles(NoneRole)
    class _FwdAction(BaseAction["_FwdAction.Params", "_FwdAction.Result"]):
        class Params(BaseParams):
            pass

        class Result(BaseResult):
            n: int = 0

        @summary_aspect("s")
        async def fwd_summary(
            self,
            params: Params,
            state: BaseState,
            box: ToolsBox,
            connections: dict[str, BaseResourceManager],
        ) -> Result:
            return BaseResult()  # type: ignore[return-value]

    with pytest.raises(ActionResultTypeError) as ei:
        await bench.run(_FwdAction(), _FwdAction.Params(), rollup=False)
    assert ei.value.expected_type is _FwdAction.Result
    assert ei.value.actual_type is BaseResult


@pytest.mark.asyncio
async def test_summary_contract_violation_still_unwinds_saga(bench: TestBench) -> None:
    """Wrong summary Result type must run compensators before raising (no partial commit)."""
    rollback_calls: list[str] = []

    @meta(description="saga then bad summary", domain=TestDomain)
    @check_roles(NoneRole)
    class _SagaWrongSummaryAction(BaseAction[_P, _R]):
        @regular_aspect("t")
        async def t_aspect(
            self,
            params: _P,
            state: BaseState,
            box: ToolsBox,
            connections: dict[str, BaseResourceManager],
        ) -> dict[str, str]:
            return {}

        @compensate("t_aspect", "rollback")
        async def rollback_t_aspect_compensate(
            self,
            params: _P,
            state_before: BaseState,
            state_after: BaseState,
            box: ToolsBox,
            connections: dict[str, BaseResourceManager],
            error: Exception,
        ) -> None:
            rollback_calls.append("rollback")

        @summary_aspect("s")
        async def build_bad_after_saga_summary(
            self,
            params: _P,
            state: BaseState,
            box: ToolsBox,
            connections: dict[str, BaseResourceManager],
        ) -> _R:
            return _WrongR()  # type: ignore[return-value]

    with pytest.raises(ActionResultTypeError):
        await bench.run(_SagaWrongSummaryAction(), _P(), rollup=False)

    assert rollback_calls == ["rollback"]


@pytest.mark.asyncio
async def test_summary_contract_violation_without_compensators_does_not_call_saga(
    bench: TestBench,
) -> None:
    """No saga frames → rollback path is a no-op; compensator must not run."""
    rollback_calls: list[str] = []

    @meta(description="no compensate, bad summary", domain=TestDomain)
    @check_roles(NoneRole)
    class _NoCompensateWrongSummaryAction(BaseAction[_P, _R]):
        @regular_aspect("t")
        async def t_only_aspect(
            self,
            params: _P,
            state: BaseState,
            box: ToolsBox,
            connections: dict[str, BaseResourceManager],
        ) -> dict[str, str]:
            return {}

        @summary_aspect("s")
        async def bad_return_summary(
            self,
            params: _P,
            state: BaseState,
            box: ToolsBox,
            connections: dict[str, BaseResourceManager],
        ) -> _R:
            return _WrongR()  # type: ignore[return-value]

    with pytest.raises(ActionResultTypeError):
        await bench.run(_NoCompensateWrongSummaryAction(), _P(), rollup=False)

    assert rollback_calls == []


@pytest.mark.asyncio
async def test_missing_summary_aspect_unwinds_saga_when_compensators_exist(
    bench: TestBench,
) -> None:
    """Missing summary for custom R after regular aspects must still compensate."""
    rollback_calls: list[str] = []

    @meta(description="no summary custom R + saga", domain=TestDomain)
    @check_roles(NoneRole)
    class _MissingSummarySagaAction(BaseAction[_P, _R]):
        @regular_aspect("t")
        async def t_aspect_only_aspect(
            self,
            params: _P,
            state: BaseState,
            box: ToolsBox,
            connections: dict[str, BaseResourceManager],
        ) -> dict[str, str]:
            return {}

        @compensate("t_aspect_only_aspect", "rollback")
        async def t_aspect_only_aspect_compensate(
            self,
            params: _P,
            state_before: BaseState,
            state_after: BaseState,
            box: ToolsBox,
            connections: dict[str, BaseResourceManager],
            error: Exception,
        ) -> None:
            rollback_calls.append("rollback")

    with pytest.raises(MissingSummaryAspectError):
        await bench.run(_MissingSummarySagaAction(), _P(), rollup=False)

    assert rollback_calls == ["rollback"]
