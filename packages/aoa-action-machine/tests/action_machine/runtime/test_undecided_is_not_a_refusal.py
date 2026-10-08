# packages/aoa-action-machine/tests/action_machine/runtime/test_undecided_is_not_a_refusal.py
"""
A gate that cannot complete is undecided — never refused, and never remembered (FR-006,
SC-004).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

"could not tell" is a third outcome, and it has to behave like one:

- it is published as ``undecided``, so a caller branching on the word never reads it as
  a refusal — whether the gate raised outright or answered undecided itself;
- it is not stored: no cache keeps it, and the next call is decided afresh, which is what
  lets a service come back without a restart;
- no path returns it as ``refused`` — not the advance answer, not the executed outcome.

The hundred runs below are the requirement's own sample: half the gates raise, half answer
``undecided`` from inside.

═══════════════════════════════════════════════════════════════════════════════
STRUCTURE
═══════════════════════════════════════════════════════════════════════════════

TestItIsUndecided       — a hundred failures, every one undecided, none a refusal
TestItIsNotRemembered   — the same call is decided afresh, and a failure fills no cache
TestNoPathCallsItRefused — neither the advance answer nor the executed outcome
"""

from __future__ import annotations

from typing import Any

import pytest

from aoa.action_machine.context.context import Context
from aoa.action_machine.context.user_info import UserInfo
from aoa.action_machine.exceptions import AccessDenied, AccessUndecided
from aoa.action_machine.intents.access_control import Allowed, Gate, Refused, Undecided, Verdict
from aoa.action_machine.intents.access_decide import access_decide
from aoa.action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta.meta_decorator import meta
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.base_result import BaseResult
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.action_machine.runtime.cache_coordinator import CacheCoordinator
from aoa.action_machine.runtime.tools_box import ToolsBox

from ...support.domain_model.domains import SystemDomain
from ...support.domain_model.roles import AdminRole

_SECRET = "postgres://primary:5432 refused the connection"
"""The failure's text: a reader in process may see it, an answer never may."""

_CHECK_CALLS = 0
_SUMMARY_CALLS = 0
_HEAL_AFTER: int | None = None
"""After how many checks the gate starts answering again; ``None`` means never."""
_FAILURE_STYLE = "raise"
"""How the gate fails: ``raise`` outright, or ``answer`` undecided from inside."""


@meta(description="undecided: a gate that fails and recovers", domain=SystemDomain)
@check_roles(AdminRole)
class UnstableGateAction(BaseAction["UnstableGateAction.Params", "UnstableGateAction.Result"]):
    """An operation whose object check fails until the test lets it answer."""

    class Params(BaseParams):
        """No inputs."""

    class Result(BaseResult):
        """No outputs."""

    @access_decide
    async def unstable_access_decide(
        self,
        params: UnstableGateAction.Params,
        context: Context,
        box: ToolsBox,
        connections: dict[str, Any],
    ) -> Verdict:
        """Fail the way the test asks, until it asks for an answer instead."""
        global _CHECK_CALLS
        _CHECK_CALLS += 1
        if _HEAL_AFTER is not None and _CHECK_CALLS > _HEAL_AFTER:
            return Allowed()
        if _FAILURE_STYLE == "answer":
            return Undecided(gate=Gate.ACCESS_DECIDE)
        raise ConnectionError(_SECRET)

    @summary_aspect("S")
    async def unstable_summary(
        self, params: UnstableGateAction.Params, state: BaseState, box: ToolsBox, connections: dict[str, Any]
    ) -> UnstableGateAction.Result:
        """Produce the operation's result, counting how often the pipeline really ran."""
        global _SUMMARY_CALLS
        _SUMMARY_CALLS += 1
        return UnstableGateAction.Result()


def _admin() -> Context:
    """The caller the probe's role requirement admits."""
    return Context(user=UserInfo(user_id="u-1", roles=(AdminRole,)))


def _machine(*, with_cache: bool = False) -> ActionProductMachine:
    """A machine, with or without a cache behind it."""
    if with_cache:
        return ActionProductMachine(cache_coordinator=CacheCoordinator())
    return ActionProductMachine(cache_coordinator=None)


def _aim(*, style: str = "raise", heal_after: int | None = None) -> None:
    """Aim the gate for one test: how it fails, and whether it recovers."""
    global _CHECK_CALLS, _SUMMARY_CALLS, _HEAL_AFTER, _FAILURE_STYLE
    _CHECK_CALLS = 0
    _SUMMARY_CALLS = 0
    _HEAL_AFTER = heal_after
    _FAILURE_STYLE = style


def _fail_style(style: str) -> None:
    """Change how the gate fails, leaving what has already been counted alone."""
    global _FAILURE_STYLE
    _FAILURE_STYLE = style


@pytest.fixture(autouse=True)
def _reset_aim() -> Any:
    """Every test starts from a gate that fails outright and never recovers."""
    _aim()
    yield
    _aim()


class TestItIsUndecided:
    async def test_a_hundred_failures_are_all_undecided(self) -> None:
        """SC-004's own sample: fifty gates raise, fifty answer undecided from inside."""
        machine = _machine()
        answers: list[Verdict] = []
        for index in range(100):
            _aim(style="raise" if index % 2 == 0 else "answer")

            answers.append(
                await machine.check_access_decide(_admin(), UnstableGateAction, UnstableGateAction.Params())
            )

        assert len(answers) == 100
        assert all(isinstance(answer, Undecided) for answer in answers)
        assert all(answer.kind == "undecided" for answer in answers)

    async def test_none_of_them_is_read_as_a_refusal(self) -> None:
        machine = _machine()
        for style in ("raise", "answer"):
            _aim(style=style)

            answer = await machine.check_access_decide(_admin(), UnstableGateAction, UnstableGateAction.Params())

            assert not isinstance(answer, Refused)
            assert answer.kind != "refused"

    async def test_the_word_names_the_step_that_could_not_tell(self) -> None:
        machine = _machine()
        for style in ("raise", "answer"):
            _aim(style=style)

            answer = await machine.check_access_decide(_admin(), UnstableGateAction, UnstableGateAction.Params())

            assert isinstance(answer, Undecided)
            assert answer.gate is Gate.ACCESS_DECIDE

    async def test_a_gate_that_raised_keeps_the_failure_in_process_only(self) -> None:
        """Raising and answering undecided reach the caller as the same word."""
        machine = _machine()
        answers = []
        for style in ("raise", "answer"):
            _aim(style=style)
            answers.append(
                await machine.check_access_decide(_admin(), UnstableGateAction, UnstableGateAction.Params())
            )

        assert all(isinstance(answer, Undecided) for answer in answers)
        assert answers[0].model_dump() == answers[1].model_dump()


class TestItIsNotRemembered:
    async def test_the_same_call_is_decided_afresh(self) -> None:
        """A failure is not an answer to reuse: the next call asks the gate again."""
        machine = _machine(with_cache=True)
        _aim(style="raise", heal_after=1)

        first = await machine.check_access_decide(_admin(), UnstableGateAction, UnstableGateAction.Params())
        second = await machine.check_access_decide(_admin(), UnstableGateAction, UnstableGateAction.Params())

        assert isinstance(first, Undecided)
        assert not isinstance(second, Undecided)
        assert _CHECK_CALLS == 2

    async def test_a_recovered_gate_lets_the_call_through(self) -> None:
        """The gate heals, the call runs: nothing remembered the failure."""
        machine = _machine(with_cache=True)
        _aim(style="raise", heal_after=1)
        with pytest.raises((AccessDenied, AccessUndecided)):
            await machine.run(_admin(), UnstableGateAction(), UnstableGateAction.Params())

        result = await machine.run(_admin(), UnstableGateAction(), UnstableGateAction.Params())

        assert isinstance(result, UnstableGateAction.Result)
        assert _SUMMARY_CALLS == 1

    async def test_a_hundred_failures_fill_no_cache(self) -> None:
        """Zero are stored or reused: the pipeline never runs behind a failure."""
        machine = _machine(with_cache=True)
        for index in range(100):
            _aim(style="raise" if index % 2 == 0 else "answer")

            await machine.check_access_decide(_admin(), UnstableGateAction, UnstableGateAction.Params())

        assert _SUMMARY_CALLS == 0

    async def test_a_hundred_failing_runs_all_ask_the_gate_again(self) -> None:
        """Every run reaches the gate: a hundred calls, a hundred checks."""
        machine = _machine(with_cache=True)
        for index in range(100):
            _fail_style("raise" if index % 2 == 0 else "answer")

            with pytest.raises((AccessDenied, AccessUndecided)):
                await machine.run(_admin(), UnstableGateAction(), UnstableGateAction.Params())

        assert _CHECK_CALLS == 100


class TestNoPathCallsItRefused:
    async def test_the_advance_answer_is_not_a_refusal(self) -> None:
        machine = _machine()
        _aim(style="raise")

        answer = await machine.check_access_decide(_admin(), UnstableGateAction, UnstableGateAction.Params())

        assert isinstance(answer, Undecided)
        assert not isinstance(answer, Refused)

    async def test_the_executed_outcome_is_not_a_refusal(self) -> None:
        machine = _machine()
        _aim(style="raise")

        with pytest.raises(Exception) as raised:
            await machine.run(_admin(), UnstableGateAction(), UnstableGateAction.Params())

        assert isinstance(raised.value, AccessUndecided)
        assert not isinstance(raised.value, AccessDenied)
