# tests/core/test_action_test_machine_extra.py
import pytest

from action_machine.core.action_test_machine import ActionTestMachine
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.core.mock_action import MockAction


class DummyParams(BaseParams):
    pass
class DummyResult(BaseResult):
    pass
class DummyAction(BaseAction[DummyParams, DummyResult]):
    pass

@pytest.mark.anyio
async def test_action_test_machine_coverage():
    machine = ActionTestMachine()

    # Проверка _prepare_mock
    ma = MockAction()
    assert machine._prepare_mock(ma) is ma

    ba = DummyAction()
    assert machine._prepare_mock(ba) is ba

    res = DummyResult()
    pm1 = machine._prepare_mock(res)
    assert isinstance(pm1, MockAction)
    assert pm1.result is res

    def side_eff(p): return res
    pm2 = machine._prepare_mock(side_eff)
    assert isinstance(pm2, MockAction)
    assert pm2.side_effect is side_eff

    assert machine._prepare_mock("plain_string") == "plain_string"

    # Запуск MockAction напрямую (обходит конвейер)
    result = await machine.run(None, pm1, DummyParams())
    assert result is res
