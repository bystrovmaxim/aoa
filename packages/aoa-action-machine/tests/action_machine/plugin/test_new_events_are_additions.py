# packages/aoa-action-machine/tests/action_machine/plugin/test_new_events_are_additions.py
"""
The new events are additions: nothing that existed before this feature changed (FR-014).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A plugin written before the access core existed must keep working, and a subscriber that
knows nothing about access must see exactly what it always saw. Two claims make that true,
and both are pinned here:

- every event that existed before the feature still exists, with the same name and the
  same own fields — the inventory below was read out of the commit this feature branched
  from, so a rename, a removed event or a changed payload fails this module;
- a plugin subscribed to none of the new events behaves exactly as it did: a run of an
  operation that declares no object check publishes the pre-existing lifecycle and nothing
  new, and a handler of an old event reads the old payload unchanged.

The four names this feature adds are listed explicitly, so the module also fails when
something *else* appears without being declared.

═══════════════════════════════════════════════════════════════════════════════
STRUCTURE
═══════════════════════════════════════════════════════════════════════════════

TestNothingOldChanged         — the frozen inventory, checked against the live module
TestTheAdditionsAreTheOnesDeclared — exactly four new names, no collision
TestAPluginThatKnowsNothingNew — the old stream, the old fields, the old handler
"""

from __future__ import annotations

import inspect
from dataclasses import fields
from typing import Any

import pytest

from aoa.action_machine.context.context import Context
from aoa.action_machine.context.user_info import UserInfo
from aoa.action_machine.intents.access_control import Allowed, Verdict
from aoa.action_machine.intents.access_decide import access_decide
from aoa.action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta.meta_decorator import meta
from aoa.action_machine.intents.on.on_decorator import on
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.base_result import BaseResult
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.plugin.core import events as events_module
from aoa.action_machine.plugin.core.events import BasePluginEvent, GlobalFinishEvent
from aoa.action_machine.plugin.core.plugin import Plugin
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.action_machine.runtime.tools_box import ToolsBox

from ...support.domain_model.domains import SystemDomain
from ...support.domain_model.roles import AdminRole

_BEFORE_THIS_FEATURE: dict[str, list[str]] = {
    "BasePluginEvent": ["action_class", "action_name", "nest_level", "context", "params"],
    "GlobalLifecycleEvent": [],
    "GlobalStartEvent": [],
    "GlobalFinishEvent": ["result", "duration_ms", "all_aspect_states"],
    "AspectEvent": ["aspect_name", "state_snapshot"],
    "RegularAspectEvent": [],
    "BeforeRegularAspectEvent": [],
    "AfterRegularAspectEvent": ["aspect_result", "duration_ms", "opaque_fields"],
    "SummaryAspectEvent": [],
    "BeforeSummaryAspectEvent": [],
    "AfterSummaryAspectEvent": ["result", "duration_ms"],
    "OnErrorAspectEvent": [],
    "BeforeOnErrorAspectEvent": ["error", "handler_name"],
    "AfterOnErrorAspectEvent": ["error", "handler_name", "handler_result", "duration_ms"],
    "CompensateAspectEvent": [],
    "BeforeCompensateAspectEvent": [
        "error",
        "compensator_name",
        "compensator_state_before",
        "compensator_state_after",
    ],
    "AfterCompensateAspectEvent": ["error", "compensator_name", "duration_ms"],
    "CompensateFailedEvent": ["original_error", "compensator_error", "compensator_name", "failed_for_aspect"],
    "SagaEvent": [],
    "SagaRollbackStartedEvent": ["error", "stack_depth", "compensator_count", "aspect_names"],
    "SagaRollbackCompletedEvent": [
        "error",
        "total_frames",
        "succeeded",
        "failed",
        "skipped",
        "duration_ms",
        "failed_aspects",
    ],
    "ErrorEvent": [],
    "UnhandledErrorEvent": ["error", "failed_aspect_name"],
}
"""Every event class of the commit this feature branched from, with its own fields.

Read out of ``9cd0fc74`` — the base commit — so this module answers one question: did the
access core change anything a plugin could already have been reading?
"""

_ADDED_BY_THIS_FEATURE = frozenset(
    {
        "AccessDecideAspectEvent",
        "BeforeAccessDecideAspectEvent",
        "AfterAccessDecideAspectEvent",
        "AccessGateFailedEvent",
    }
)
"""The four events the access core adds, and nothing else."""

_SEEN_NAMES: list[str] = []
_FINISH_PAYLOAD: dict[str, Any] = {}


def _own_fields(cls: type) -> list[str]:
    """The fields a class declares itself, in declaration order (inherited ones excluded)."""
    return list(cls.__dict__.get("__annotations__", {}).keys())


def _all_events() -> dict[str, type]:
    """Every event class the module defines, by name."""
    return {
        name: member
        for name, member in vars(events_module).items()
        if inspect.isclass(member) and issubclass(member, BasePluginEvent)
    }


@meta(description="additions: an operation that declares no object check", domain=SystemDomain)
@check_roles(AdminRole)
class PlainSummaryAction(BaseAction["PlainSummaryAction.Params", "PlainSummaryAction.Result"]):
    """An operation from before the access core: a role, a summary, nothing else."""

    class Params(BaseParams):
        """No inputs."""

    class Result(BaseResult):
        """No outputs."""

    @summary_aspect("S")
    async def plain_summary(
        self, params: PlainSummaryAction.Params, state: BaseState, box: ToolsBox, connections: dict[str, Any]
    ) -> PlainSummaryAction.Result:
        """Produce the operation's result."""
        return PlainSummaryAction.Result()


@meta(description="additions: an operation that declares an object check", domain=SystemDomain)
@check_roles(AdminRole)
class CheckedSummaryAction(BaseAction["CheckedSummaryAction.Params", "CheckedSummaryAction.Result"]):
    """The same operation with an access declaration on it."""

    class Params(BaseParams):
        """No inputs."""

    class Result(BaseResult):
        """No outputs."""

    @access_decide
    async def checked_access_decide(
        self,
        params: CheckedSummaryAction.Params,
        context: Context,
        box: ToolsBox,
        connections: dict[str, Any],
    ) -> Verdict:
        """Allow every caller the role requirement admitted."""
        return Allowed()

    @summary_aspect("S")
    async def checked_summary(
        self, params: CheckedSummaryAction.Params, state: BaseState, box: ToolsBox, connections: dict[str, Any]
    ) -> CheckedSummaryAction.Result:
        """Produce the operation's result."""
        return CheckedSummaryAction.Result()


class BroadRecorder(Plugin):
    """A plugin written against the root event, as a logging plugin would be."""

    async def get_initial_state(self) -> dict[str, Any]:
        """Record in a module list, so a test can read it after the run."""
        return {}

    @on(BasePluginEvent, ignore_exceptions=False)
    async def on_any(self, state: dict[str, Any], event: BasePluginEvent, log: Any) -> dict[str, Any]:
        """Record one event name."""
        _SEEN_NAMES.append(type(event).__name__)
        return state


class LegacyFinishSubscriber(Plugin):
    """A plugin subscribed to one old event, reading the payload it always read."""

    async def get_initial_state(self) -> dict[str, Any]:
        """Nothing to keep between events."""
        return {}

    @on(GlobalFinishEvent, ignore_exceptions=False)
    async def on_finish(self, state: dict[str, Any], event: GlobalFinishEvent, log: Any) -> dict[str, Any]:
        """Read the fields this event has always carried."""
        _FINISH_PAYLOAD["result"] = event.result
        _FINISH_PAYLOAD["duration_ms"] = event.duration_ms
        _FINISH_PAYLOAD["all_aspect_states"] = event.all_aspect_states
        _FINISH_PAYLOAD["keys"] = sorted(field.name for field in fields(event))
        return state


@pytest.fixture(autouse=True)
def _forget() -> Any:
    """Forget what a previous test saw."""
    _SEEN_NAMES.clear()
    _FINISH_PAYLOAD.clear()
    yield
    _SEEN_NAMES.clear()
    _FINISH_PAYLOAD.clear()


def _admin() -> Context:
    """A caller holding the role both probes list."""
    return Context(user=UserInfo(user_id="u-1", roles=(AdminRole,)))


def _machine(*plugins: Plugin) -> ActionProductMachine:
    """A machine watched by the given plugins."""
    return ActionProductMachine(cache_coordinator=None, plugins=list(plugins))


class TestNothingOldChanged:
    @pytest.mark.parametrize("name", sorted(_BEFORE_THIS_FEATURE))
    def test_the_event_still_exists_with_its_own_fields(self, name: str) -> None:
        live = _all_events()

        assert name in live, f"{name} disappeared"
        assert _own_fields(live[name]) == _BEFORE_THIS_FEATURE[name]

    def test_the_module_defines_the_old_events_and_the_new_ones(self) -> None:
        live = set(_all_events())

        assert live == set(_BEFORE_THIS_FEATURE) | _ADDED_BY_THIS_FEATURE

    def test_no_old_event_gained_or_lost_a_field(self) -> None:
        live = _all_events()

        changed = {
            name: (frozen, _own_fields(live[name]))
            for name, frozen in _BEFORE_THIS_FEATURE.items()
            if _own_fields(live[name]) != frozen
        }

        assert changed == {}


class TestTheAdditionsAreTheOnesDeclared:
    def test_exactly_four_names_were_added(self) -> None:
        assert set(_all_events()) - set(_BEFORE_THIS_FEATURE) == _ADDED_BY_THIS_FEATURE

    def test_no_addition_reuses_an_old_name(self) -> None:
        assert _ADDED_BY_THIS_FEATURE & set(_BEFORE_THIS_FEATURE) == set()

    def test_every_addition_is_an_event(self) -> None:
        live = _all_events()

        for name in _ADDED_BY_THIS_FEATURE:
            assert issubclass(live[name], BasePluginEvent)


class TestAPluginThatKnowsNothingNew:
    async def test_an_operation_without_a_check_publishes_none_of_the_new_events(self) -> None:
        """A plugin written before the feature sees exactly its old stream."""
        machine = _machine(BroadRecorder())

        await machine.run(_admin(), PlainSummaryAction(), PlainSummaryAction.Params())

        assert set(_SEEN_NAMES) & _ADDED_BY_THIS_FEATURE == set()

    async def test_the_old_lifecycle_is_what_it_always_was(self) -> None:
        machine = _machine(BroadRecorder())

        await machine.run(_admin(), PlainSummaryAction(), PlainSummaryAction.Params())

        assert _SEEN_NAMES == [
            "GlobalStartEvent",
            "BeforeSummaryAspectEvent",
            "AfterSummaryAspectEvent",
            "GlobalFinishEvent",
        ]

    async def test_a_legacy_handler_reads_the_payload_it_always_read(self) -> None:
        machine = _machine(LegacyFinishSubscriber())

        await machine.run(_admin(), PlainSummaryAction(), PlainSummaryAction.Params())

        assert set(_FINISH_PAYLOAD) == {"result", "duration_ms", "all_aspect_states", "keys"}
        assert _FINISH_PAYLOAD["keys"] == sorted(
            {
                "action_class",
                "action_name",
                "nest_level",
                "context",
                "params",
                "result",
                "duration_ms",
                "all_aspect_states",
            }
        )

    async def test_a_declared_check_adds_events_without_taking_any_away(self) -> None:
        """The same operation with a declaration: the old stream is still there, plus two."""
        machine = _machine(BroadRecorder())

        await machine.run(_admin(), CheckedSummaryAction(), CheckedSummaryAction.Params())

        assert _SEEN_NAMES == [
            "GlobalStartEvent",
            "BeforeAccessDecideAspectEvent",
            "AfterAccessDecideAspectEvent",
            "BeforeSummaryAspectEvent",
            "AfterSummaryAspectEvent",
            "GlobalFinishEvent",
        ]
