# tests/model/test_navigation_performance.py

import time

import pytest

from action_machine.intents.context.context import Context
from action_machine.intents.logging.log_scope import LogScope
from action_machine.intents.logging.variable_substitutor import VariableSubstitutor
from action_machine.model.base_params import BaseParams
from action_machine.model.base_state import BaseState

pytestmark = pytest.mark.benchmark


class TestNavigationPerformance:
    """Бенчмарки навигации — доказательство что кеш не нужен."""

    def test_resolve_10k_calls_under_100ms(self) -> None:
        """10 000 вызовов resolve() укладываются в 100мс."""
        st = BaseState(nested={"deep": {"value": 42}})

        start = time.perf_counter()
        for _ in range(10_000):
            st.resolve("nested.deep.value")
        elapsed = time.perf_counter() - start

        assert elapsed < 0.1, f"10k resolve() заняли {elapsed:.3f}с (лимит 0.1с)"

    def test_substitute_1k_calls_under_500ms(self) -> None:
        """1 000 вызовов substitute() укладываются в 500мс."""
        sub = VariableSubstitutor()
        scope = LogScope(machine="M", mode="t", action="A", aspect="a", nest_level=0)
        ctx = Context()
        st = BaseState(count=42)
        params = BaseParams()
        template = "User: {%context.user.user_id}, Count: {%state.count}"

        start = time.perf_counter()
        for _ in range(1_000):
            sub.substitute(template, {}, scope, ctx, st, params)
        elapsed = time.perf_counter() - start

        assert elapsed < 0.5, f"1k substitute() заняли {elapsed:.3f}с (лимит 0.5с)"

    def test_resolve_falsy_values_same_speed_as_regular(self) -> None:
        """Falsy-значения (0, False, None) не замедляют навигацию."""
        st_regular = BaseState(value="hello")
        st_falsy = BaseState(value=0)

        start = time.perf_counter()
        for _ in range(10_000):
            st_regular.resolve("value")
        time_regular = time.perf_counter() - start

        start = time.perf_counter()
        for _ in range(10_000):
            st_falsy.resolve("value")
        time_falsy = time.perf_counter() - start

        # Falsy не должно быть медленнее более чем в 2 раза
        assert time_falsy < time_regular * 2
