# tests/action_machine/model/test_base_action_access_decide.py
"""Unit tests for the default ``access_decide`` hook on ``BaseAction``."""

from __future__ import annotations

import pytest

from aoa.action_machine.context.context import Context
from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.intents.access_control import AllowedVerdict, FailSecurityVerdict
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.model.params_stub import ParamsStub
from aoa.action_machine.model.result_stub import ResultStub


@exclude_graph_model
class DefaultAccessDecideAction(BaseAction[ParamsStub, ResultStub]):
    """Concrete action using the default access_decide implementation."""

    pass


@exclude_graph_model
class DenyingAccessDecideAction(BaseAction[ParamsStub, ResultStub]):
    async def access_decide(
        self,
        params: ParamsStub,
        context: Context,
        box: object,
        connections: dict[str, object],
    ) -> FailSecurityVerdict | AllowedVerdict:
        return FailSecurityVerdict("denied")


class TestDefaultAccessDecide:
    @pytest.mark.asyncio
    async def test_default_access_decide_returns_allowed(self) -> None:
        got = await DefaultAccessDecideAction().access_decide(ParamsStub(), Context(), None, {})
        assert got == AllowedVerdict()


class TestSubclassAccessDecide:
    @pytest.mark.asyncio
    async def test_subclass_can_deny_access(self) -> None:
        got = await DenyingAccessDecideAction().access_decide(ParamsStub(), Context(), None, {})
        assert got == FailSecurityVerdict("denied")
