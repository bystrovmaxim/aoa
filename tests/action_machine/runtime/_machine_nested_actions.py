# tests/runtime/_machine_nested_actions.py
"""Test-only actions for nested ToolsBox.run() scenarios."""

from __future__ import annotations

from pydantic import Field

from aoa.action_machine.intents.aspects.regular_aspect_decorator import regular_aspect
from aoa.action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from aoa.action_machine.intents.check_roles import NoneRole, check_roles
from aoa.action_machine.intents.checkers import result_string
from aoa.action_machine.intents.meta.meta_decorator import meta
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.base_result import BaseResult
from tests.action_machine.scenarios.domain_model.domains import TestDomain


class ChildNestedParams(BaseParams):
    """Parameters for the child action in nested-run tests."""

    pass


class ChildNestedResult(BaseResult):
    """Child action result (frozen); fields set in the constructor."""

    child_data: str = Field(description="Data from child action")
    nest: int = Field(description="Nesting level")


@meta(description="Child action for nested-run tests", domain=TestDomain)
@check_roles(NoneRole)
class ChildNestedTestAction(BaseAction[ChildNestedParams, ChildNestedResult]):
    """Simple child action returning a fixed result via constructor."""

    @summary_aspect("Child summary")
    async def build_summary(self, params, state, box, connections):
        return ChildNestedResult(child_data="from_child", nest=box.nested_level)


class ParentNestedParams(BaseParams):
    """Parameters for the parent action."""

    pass


class ParentNestedResult(BaseResult):
    """Parent result (frozen)."""

    combined: str = Field(description="Combined outcome")
    parent_nest: int = Field(description="Parent nesting level")


@meta(description="Parent calling child via box.run()", domain=TestDomain)
@check_roles(NoneRole)
class ParentNestedTestAction(BaseAction[ParentNestedParams, ParentNestedResult]):
    """Regular aspect runs ChildNestedTestAction via box.run()."""

    @regular_aspect("Call child")
    @result_string("child_result", required=True)
    async def call_child_aspect(self, params, state, box, connections):
        child_result = await box.run(ChildNestedTestAction, ChildNestedParams())
        return {"child_result": child_result.child_data}

    @summary_aspect("Parent summary")
    async def build_summary(self, params, state, box, connections):
        return ParentNestedResult(
            combined=f"parent+{state['child_result']}",
            parent_nest=box.nested_level,
        )


@meta(description="Action recording nest_level in result", domain=TestDomain)
@check_roles(NoneRole)
class NestLevelTestAction(BaseAction[ChildNestedParams, ChildNestedResult]):
    """Writes current nest_level from ToolsBox into the result."""

    @summary_aspect("Record nest_level")
    async def build_summary(self, params, state, box, connections):
        return ChildNestedResult(child_data="", nest=box.nested_level)


@meta(description="Parent calling NestLevelTestAction", domain=TestDomain)
@check_roles(NoneRole)
class NestLevelParentAction(BaseAction[ParentNestedParams, ParentNestedResult]):
    """Runs NestLevelTestAction and records parent vs child nest levels."""

    @regular_aspect("Call nest-level child")
    @result_string("info", required=True)
    async def call_child_aspect(self, params, state, box, connections):
        child_result = await box.run(NestLevelTestAction, ChildNestedParams())
        child_nest = child_result.nest
        return {"info": f"parent={box.nested_level},child={child_nest}"}

    @summary_aspect("Summary")
    async def build_summary(self, params, state, box, connections):
        return ParentNestedResult(combined=state["info"], parent_nest=box.nested_level)
