# tests/smoke/test_ping.py
"""
Smoke-тест PingAction — минимальное действие.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Проверяет базовый конвейер ActionMachine на самом простом действии:
координатор собирает метаданные, машина выполняет единственный
summary-аспект, TestBench прогоняет на async и sync машинах
и сравнивает результаты.

PingAction не имеет параметров, зависимостей, connections и ролевых
ограничений (NoneRole). Если этот тест красный — сломано что-то
фундаментальное.
"""

import pytest

from action_machine.testing import TestBench
from tests.domain_model import PingAction


@pytest.mark.asyncio
async def test_ping_returns_pong(bench: TestBench) -> None:
    """
    PingAction возвращает Result с message='pong'.

    Проверяет полный цикл: сборка метаданных → проверка ролей
    (NoneRole) → выполнение summary-аспекта → формирование Result.
    TestBench прогоняет на async и sync машинах и сравнивает.
    """
    # Arrange
    action = PingAction()
    params = PingAction.Params()

    # Act
    result = await bench.run(action, params, rollup=False)

    # Assert
    assert result.message == "pong"


@pytest.mark.asyncio
async def test_ping_result_type(bench: TestBench) -> None:
    """
    PingAction возвращает экземпляр PingAction.Result.

    Проверяет, что результат — конкретный тип Result,
    а не произвольный BaseResult или dict.
    """
    # Arrange
    action = PingAction()
    params = PingAction.Params()

    # Act
    result = await bench.run(action, params, rollup=False)

    # Assert
    assert isinstance(result, PingAction.Result)
