# tests/action_machine/runtime/test_include_contract_checker.py
"""PR-4: ``IncludeContractChecker`` and include-contract integration with ``ActionProductMachine``."""

from __future__ import annotations

import asyncio

import pytest
from pydantic import Field

from aoa.action_machine.context.context import Context
from aoa.action_machine.context.user_info import UserInfo
from aoa.action_machine.exceptions.include_contract_violation_error import IncludeContractViolationError
from aoa.action_machine.intents.aspects.regular_aspect_decorator import regular_aspect
from aoa.action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from aoa.action_machine.intents.check_roles import NoneRole, check_roles
from aoa.action_machine.intents.depends import UseCase, depends
from aoa.action_machine.intents.meta.meta_decorator import meta
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.base_result import BaseResult
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.action_machine.runtime.include_contract_checker import IncludeContractChecker
from aoa.action_machine.runtime.tools_box import ToolsBox
from tests.action_machine.scenarios.domain_model.domains import SystemDomain
from tests.action_machine.scenarios.domain_model.roles import AdminRole, ManagerRole


def _ctx() -> Context:
    return Context(user=UserInfo(user_id="u", roles=(ManagerRole, AdminRole)))


# ── leaf actions (minimal summary-only) ─────────────────────────────────────


@meta(description="leaf A for include gather tests", domain=SystemDomain)
@check_roles(NoneRole)
class LeafAForGatherAction(BaseAction["LeafAForGatherAction.Params", "LeafAForGatherAction.Result"]):
    class Params(BaseParams):
        pass

    class Result(BaseResult):
        tag: str = Field(default="a")

    @summary_aspect("s")
    async def s_summary(
        self,
        params: LeafAForGatherAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> LeafAForGatherAction.Result:
        return LeafAForGatherAction.Result()


@meta(description="leaf B for include gather tests", domain=SystemDomain)
@check_roles(NoneRole)
class LeafBForGatherAction(BaseAction["LeafBForGatherAction.Params", "LeafBForGatherAction.Result"]):
    class Params(BaseParams):
        pass

    class Result(BaseResult):
        tag: str = Field(default="b")

    @summary_aspect("s")
    async def s_summary(
        self,
        params: LeafBForGatherAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> LeafBForGatherAction.Result:
        return LeafBForGatherAction.Result()


@meta(description="leaf for include contract tests", domain=SystemDomain)
@check_roles(NoneRole)
class LeafForContractAction(BaseAction["LeafForContractAction.Params", "LeafForContractAction.Result"]):
    class Params(BaseParams):
        pass

    class Result(BaseResult):
        ok: str = Field(default="leaf")

    @summary_aspect("s")
    async def s_summary(
        self,
        params: LeafForContractAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> LeafForContractAction.Result:
        return LeafForContractAction.Result()


# ── checker unit tests ────────────────────────────────────────────────────────


def test_include_contract_checker_noop_when_no_include_deps() -> None:
    IncludeContractChecker.verify(LeafForContractAction(), frozenset())


def test_include_contract_checker_ok_when_types_present() -> None:
    IncludeContractChecker.verify(
        HostIncludeSingleAction(),
        frozenset({HostIncludeSingleAction, LeafForContractAction}),
    )


def test_include_contract_checker_single_missing() -> None:
    with pytest.raises(IncludeContractViolationError) as excinfo:
        IncludeContractChecker.verify(
            HostIncludeSingleAction(),
            frozenset({HostIncludeSingleAction}),
        )
    assert excinfo.value.missing_include_types == frozenset({LeafForContractAction})


def test_include_contract_checker_multiple_missing() -> None:
    with pytest.raises(IncludeContractViolationError) as excinfo:
        IncludeContractChecker.verify(
            HostIncludeTwoAction(),
            frozenset({HostIncludeTwoAction}),
        )
    assert excinfo.value.missing_include_types == frozenset({LeafAForGatherAction, LeafBForGatherAction})


@meta(description="host single include", domain=SystemDomain)
@check_roles(NoneRole)
@depends(LeafForContractAction, mode=UseCase.include, description="d")
class HostIncludeSingleAction(BaseAction["HostIncludeSingleAction.Params", "HostIncludeSingleAction.Result"]):
    class Params(BaseParams):
        pass

    class Result(BaseResult):
        ok: str = Field(default="x")

    @summary_aspect("s")
    async def s_summary(
        self,
        params: HostIncludeSingleAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> HostIncludeSingleAction.Result:
        return HostIncludeSingleAction.Result()


@meta(description="host two includes", domain=SystemDomain)
@check_roles(NoneRole)
@depends(LeafAForGatherAction, mode=UseCase.include, description="a")
@depends(LeafBForGatherAction, mode=UseCase.include, description="b")
class HostIncludeTwoAction(BaseAction["HostIncludeTwoAction.Params", "HostIncludeTwoAction.Result"]):
    class Params(BaseParams):
        pass

    class Result(BaseResult):
        ok: str = Field(default="x")

    @summary_aspect("s")
    async def s_summary(
        self,
        params: HostIncludeTwoAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> HostIncludeTwoAction.Result:
        return HostIncludeTwoAction.Result()


# ── machine integration ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_include_violation_when_peer_never_run() -> None:
    @meta(description="violator", domain=SystemDomain)
    @check_roles(NoneRole)
    @depends(LeafForContractAction, mode=UseCase.include, description="must run leaf")
    class IncludeViolatorAction(
        BaseAction["IncludeViolatorAction.Params", "IncludeViolatorAction.Result"]
    ):
        class Params(BaseParams):
            pass

        class Result(BaseResult):
            ok: str = Field(default="no")

        @summary_aspect("s")
        async def s_summary(
            self,
            params: IncludeViolatorAction.Params,
            state: BaseState,
            box: ToolsBox,
            connections: dict[str, BaseResource],
        ) -> IncludeViolatorAction.Result:
            return IncludeViolatorAction.Result()

    machine = ActionProductMachine()
    with pytest.raises(IncludeContractViolationError) as excinfo:
        await machine.run(_ctx(), IncludeViolatorAction(), IncludeViolatorAction.Params())
    assert excinfo.value.missing_include_types == frozenset({LeafForContractAction})


@pytest.mark.asyncio
async def test_include_ok_when_box_run_peer() -> None:
    @meta(description="runner", domain=SystemDomain)
    @check_roles(NoneRole)
    @depends(LeafForContractAction, mode=UseCase.include, description="must run leaf")
    class IncludeRunnerAction(BaseAction["IncludeRunnerAction.Params", "IncludeRunnerAction.Result"]):
        class Params(BaseParams):
            pass

        class Result(BaseResult):
            ok: str = Field(default="yes")

        @summary_aspect("s")
        async def s_summary(
            self,
            params: IncludeRunnerAction.Params,
            state: BaseState,
            box: ToolsBox,
            connections: dict[str, BaseResource],
        ) -> IncludeRunnerAction.Result:
            await box.run(LeafForContractAction, LeafForContractAction.Params())
            return IncludeRunnerAction.Result()

    machine = ActionProductMachine()
    result = await machine.run(_ctx(), IncludeRunnerAction(), IncludeRunnerAction.Params())
    assert result.ok == "yes"


@pytest.mark.asyncio
async def test_extend_not_enforced_by_include_checker() -> None:
    @meta(description="extend host", domain=SystemDomain)
    @check_roles(NoneRole)
    @depends(LeafForContractAction, mode=UseCase.extend, description="optional")
    class ExtendHostAction(BaseAction["ExtendHostAction.Params", "ExtendHostAction.Result"]):
        class Params(BaseParams):
            pass

        class Result(BaseResult):
            ok: str = Field(default="ext")

        @summary_aspect("s")
        async def s_summary(
            self,
            params: ExtendHostAction.Params,
            state: BaseState,
            box: ToolsBox,
            connections: dict[str, BaseResource],
        ) -> ExtendHostAction.Result:
            return ExtendHostAction.Result()

    machine = ActionProductMachine()
    result = await machine.run(_ctx(), ExtendHostAction(), ExtendHostAction.Params())
    assert result.ok == "ext"


@pytest.mark.asyncio
async def test_include_transitive_success_when_nested_runs_leaf() -> None:
    @meta(description="middle runs leaf", domain=SystemDomain)
    @check_roles(NoneRole)
    class MiddleRunsLeafAction(BaseAction["MiddleRunsLeafAction.Params", "MiddleRunsLeafAction.Result"]):
        class Params(BaseParams):
            pass

        class Result(BaseResult):
            mid: str = Field(default="m")

        @regular_aspect("run leaf")
        async def run_leaf_aspect(
            self,
            params: MiddleRunsLeafAction.Params,
            state: BaseState,
            box: ToolsBox,
            connections: dict[str, BaseResource],
        ) -> dict:
            await box.run(LeafForContractAction, LeafForContractAction.Params())
            return {}

        @summary_aspect("s")
        async def s_summary(
            self,
            params: MiddleRunsLeafAction.Params,
            state: BaseState,
            box: ToolsBox,
            connections: dict[str, BaseResource],
        ) -> MiddleRunsLeafAction.Result:
            return MiddleRunsLeafAction.Result()

    @meta(description="root transitive ok", domain=SystemDomain)
    @check_roles(NoneRole)
    @depends(LeafForContractAction, mode=UseCase.include, description="leaf anywhere in tree")
    class RootTransitiveOkAction(BaseAction["RootTransitiveOkAction.Params", "RootTransitiveOkAction.Result"]):
        class Params(BaseParams):
            pass

        class Result(BaseResult):
            ok: str = Field(default="root")

        @regular_aspect("middle")
        async def run_middle_aspect(
            self,
            params: RootTransitiveOkAction.Params,
            state: BaseState,
            box: ToolsBox,
            connections: dict[str, BaseResource],
        ) -> dict:
            await box.run(MiddleRunsLeafAction, MiddleRunsLeafAction.Params())
            return {}

        @summary_aspect("s")
        async def s_summary(
            self,
            params: RootTransitiveOkAction.Params,
            state: BaseState,
            box: ToolsBox,
            connections: dict[str, BaseResource],
        ) -> RootTransitiveOkAction.Result:
            return RootTransitiveOkAction.Result()

    machine = ActionProductMachine()
    result = await machine.run(_ctx(), RootTransitiveOkAction(), RootTransitiveOkAction.Params())
    assert result.ok == "root"


@pytest.mark.asyncio
async def test_include_transitive_fails_when_leaf_never_run() -> None:
    @meta(description="middle skips leaf", domain=SystemDomain)
    @check_roles(NoneRole)
    class MiddleSkipsLeafAction(BaseAction["MiddleSkipsLeafAction.Params", "MiddleSkipsLeafAction.Result"]):
        class Params(BaseParams):
            pass

        class Result(BaseResult):
            mid: str = Field(default="m")

        @regular_aspect("noop")
        async def noop_aspect(
            self,
            params: MiddleSkipsLeafAction.Params,
            state: BaseState,
            box: ToolsBox,
            connections: dict[str, BaseResource],
        ) -> dict:
            return {}

        @summary_aspect("s")
        async def s_summary(
            self,
            params: MiddleSkipsLeafAction.Params,
            state: BaseState,
            box: ToolsBox,
            connections: dict[str, BaseResource],
        ) -> MiddleSkipsLeafAction.Result:
            return MiddleSkipsLeafAction.Result()

    @meta(description="root transitive fail", domain=SystemDomain)
    @check_roles(NoneRole)
    @depends(LeafForContractAction, mode=UseCase.include, description="leaf")
    class RootTransitiveFailAction(BaseAction["RootTransitiveFailAction.Params", "RootTransitiveFailAction.Result"]):
        class Params(BaseParams):
            pass

        class Result(BaseResult):
            ok: str = Field(default="root")

        @regular_aspect("middle")
        async def run_middle_aspect(
            self,
            params: RootTransitiveFailAction.Params,
            state: BaseState,
            box: ToolsBox,
            connections: dict[str, BaseResource],
        ) -> dict:
            await box.run(MiddleSkipsLeafAction, MiddleSkipsLeafAction.Params())
            return {}

        @summary_aspect("s")
        async def s_summary(
            self,
            params: RootTransitiveFailAction.Params,
            state: BaseState,
            box: ToolsBox,
            connections: dict[str, BaseResource],
        ) -> RootTransitiveFailAction.Result:
            return RootTransitiveFailAction.Result()

    machine = ActionProductMachine()
    with pytest.raises(IncludeContractViolationError) as excinfo:
        await machine.run(_ctx(), RootTransitiveFailAction(), RootTransitiveFailAction.Params())
    assert excinfo.value.missing_include_types == frozenset({LeafForContractAction})


@pytest.mark.asyncio
async def test_gather_merges_nested_machine_runs_into_one_tracker() -> None:
    @meta(description="gather host", domain=SystemDomain)
    @check_roles(NoneRole)
    @depends(LeafAForGatherAction, mode=UseCase.include, description="a")
    @depends(LeafBForGatherAction, mode=UseCase.include, description="b")
    class GatherIncludeHostAction(
        BaseAction["GatherIncludeHostAction.Params", "GatherIncludeHostAction.Result"]
    ):
        class Params(BaseParams):
            pass

        class Result(BaseResult):
            ok: str = Field(default="g")

        @summary_aspect("s")
        async def s_summary(
            self,
            params: GatherIncludeHostAction.Params,
            state: BaseState,
            box: ToolsBox,
            connections: dict[str, BaseResource],
        ) -> GatherIncludeHostAction.Result:
            await asyncio.gather(
                box.run(LeafAForGatherAction, LeafAForGatherAction.Params()),
                box.run(LeafBForGatherAction, LeafBForGatherAction.Params()),
            )
            return GatherIncludeHostAction.Result()

    machine = ActionProductMachine()
    result = await machine.run(_ctx(), GatherIncludeHostAction(), GatherIncludeHostAction.Params())
    assert result.ok == "g"


@pytest.mark.asyncio
async def test_create_task_awaited_still_shares_root_include_tracker() -> None:
    """CPython asyncio tasks inherit ContextVar values; awaited ``create_task(box.run)`` counts."""

    @meta(description="task host", domain=SystemDomain)
    @check_roles(NoneRole)
    @depends(LeafForContractAction, mode=UseCase.include, description="leaf")
    class CreateTaskIncludeHostAction(
        BaseAction["CreateTaskIncludeHostAction.Params", "CreateTaskIncludeHostAction.Result"]
    ):
        class Params(BaseParams):
            pass

        class Result(BaseResult):
            ok: str = Field(default="t")

        @summary_aspect("s")
        async def s_summary(
            self,
            params: CreateTaskIncludeHostAction.Params,
            state: BaseState,
            box: ToolsBox,
            connections: dict[str, BaseResource],
        ) -> CreateTaskIncludeHostAction.Result:
            task = asyncio.create_task(box.run(LeafForContractAction, LeafForContractAction.Params()))
            await task
            return CreateTaskIncludeHostAction.Result()

    machine = ActionProductMachine()
    result = await machine.run(_ctx(), CreateTaskIncludeHostAction(), CreateTaskIncludeHostAction.Params())
    assert result.ok == "t"


@pytest.mark.asyncio
async def test_resolve_only_does_not_satisfy_include() -> None:
    @meta(description="resolve only host", domain=SystemDomain)
    @check_roles(NoneRole)
    @depends(LeafForContractAction, mode=UseCase.include, description="leaf")
    class ResolveOnlyHostAction(BaseAction["ResolveOnlyHostAction.Params", "ResolveOnlyHostAction.Result"]):
        class Params(BaseParams):
            pass

        class Result(BaseResult):
            ok: str = Field(default="r")

        @summary_aspect("s")
        async def s_summary(
            self,
            params: ResolveOnlyHostAction.Params,
            state: BaseState,
            box: ToolsBox,
            connections: dict[str, BaseResource],
        ) -> ResolveOnlyHostAction.Result:
            _ = box.resolve(LeafForContractAction)
            return ResolveOnlyHostAction.Result()

    machine = ActionProductMachine()
    with pytest.raises(IncludeContractViolationError) as excinfo:
        await machine.run(_ctx(), ResolveOnlyHostAction(), ResolveOnlyHostAction.Params())
    assert LeafForContractAction in excinfo.value.missing_include_types
