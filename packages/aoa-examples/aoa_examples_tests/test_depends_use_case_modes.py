# packages/aoa-examples/aoa_examples_tests/test_depends_use_case_modes.py
"""``UseCase.extend`` vs ``UseCase.include`` on example action-to-action ``@depends`` (two domains)."""

from __future__ import annotations

import pytest

from aoa.action_machine.context.context import Context
from aoa.action_machine.context.request_info import RequestInfo
from aoa.action_machine.intents.depends import UseCase
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine

# Completes coordinator/runtime imports before ``Context`` (avoids cycles when this tree is collected alone).
from aoa.action_machine.testing import TestBench  # noqa: F401  # pylint: disable=unused-import
from aoa.examples.model.interchange_demo_coordinator import (
    build_registered_interchange_coordinator,
    import_sample_registration_modules,
)
from aoa.examples.model.store.actions.ping import OpsPingAction
from aoa.examples.model.support.actions import (
    DependCrossDomainAction,
    DependCrossDomainIncludeAction,
    DependSameDomainAction,
    DependSameDomainIncludeAction,
)
from aoa.examples.model.support.actions.support_ping import SupportPingAction


@pytest.fixture(scope="module", name="examples_machine")
def _examples_machine_fixture() -> ActionProductMachine:
    import_sample_registration_modules()
    return ActionProductMachine(graph_coordinator=build_registered_interchange_coordinator())


def _ctx_with_trace() -> Context:
    """``OpsPingAction`` summary requires ``Ctx.Request.trace_id`` when run nested."""
    return Context(request=RequestInfo(trace_id="examples-depends-trace"))


def _mode_for(machine: ActionProductMachine, host: type, dep: type) -> str | None:
    node = machine.get_action_node_by_id(host)
    for info in node.resolved_dependency_infos():
        if info.cls is dep:
            return info.mode
    raise AssertionError(f"no dependency edge {host.__name__} -> {dep.__name__}")


def test_graph_same_domain_extend_vs_include_modes(examples_machine: ActionProductMachine) -> None:
    assert _mode_for(examples_machine, DependSameDomainAction, SupportPingAction) == UseCase.extend
    assert _mode_for(examples_machine, DependSameDomainIncludeAction, SupportPingAction) == UseCase.include


def test_graph_cross_domain_extend_vs_include_modes(examples_machine: ActionProductMachine) -> None:
    assert _mode_for(examples_machine, DependCrossDomainAction, OpsPingAction) == UseCase.extend
    assert _mode_for(examples_machine, DependCrossDomainIncludeAction, OpsPingAction) == UseCase.include


@pytest.mark.asyncio
async def test_machine_same_domain_extend_resolve_only(examples_machine: ActionProductMachine) -> None:
    result = await examples_machine.run(
        _ctx_with_trace(),
        DependSameDomainAction(),
        DependSameDomainAction.Params(),
    )
    assert result.peer == SupportPingAction.__name__


@pytest.mark.asyncio
async def test_machine_same_domain_include_runs_peer(examples_machine: ActionProductMachine) -> None:
    result = await examples_machine.run(
        _ctx_with_trace(),
        DependSameDomainIncludeAction(),
        DependSameDomainIncludeAction.Params(),
    )
    assert result.peer == SupportPingAction.__name__
    assert result.peer_ok is True


@pytest.mark.asyncio
async def test_machine_cross_domain_extend_resolve_only(examples_machine: ActionProductMachine) -> None:
    result = await examples_machine.run(
        _ctx_with_trace(),
        DependCrossDomainAction(),
        DependCrossDomainAction.Params(),
    )
    assert result.peer == OpsPingAction.__name__


@pytest.mark.asyncio
async def test_machine_cross_domain_include_runs_store_peer(examples_machine: ActionProductMachine) -> None:
    result = await examples_machine.run(
        _ctx_with_trace(),
        DependCrossDomainIncludeAction(),
        DependCrossDomainIncludeAction.Params(),
    )
    assert result.peer == OpsPingAction.__name__
    assert result.pong == "pong"
