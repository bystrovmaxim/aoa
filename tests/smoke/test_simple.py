# tests/smoke/test_simple.py
"""
Smoke-тест SimpleAction — действие с одним regular-аспектом и чекером.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Проверяет конвейер из двух аспектов: regular-аспект записывает
validated_name в state, чекер result_string проверяет его,
summary-аспект формирует приветствие из state.

SimpleAction не имеет зависимостей и connections, доступен всем
(ROLE_NONE). Если этот тест красный — проблема в конвейере
regular → state → summary или в чекерах.
"""

import pytest

from action_machine.testing import TestBench
from tests.domain_model import SimpleAction


@pytest.mark.asyncio
async def test_simple_action_greeting(bench: TestBench) -> None:
    """
    SimpleAction формирует приветствие 'Hello, Alice!' из имени 'Alice'.

    Проверяет полный конвейер:
    1. validate_name (regular) → state["validated_name"] = "Alice"
    2. Чекер result_string проверяет validated_name (непустая строка).
    3. build_greeting (summary) → Result(greeting="Hello, Alice!")
    """
    # Arrange
    action = SimpleAction()
    params = SimpleAction.Params(name="Alice")

    # Act
    result = await bench.run(action, params, rollup=False)

    # Assert
    assert result.greeting == "Hello, Alice!"


@pytest.mark.asyncio
async def test_simple_action_strips_whitespace(bench: TestBench) -> None:
    """
    SimpleAction убирает пробелы по краям имени.

    Аспект validate_name вызывает params.name.strip(), поэтому
    имя с пробелами '  Bob  ' превращается в 'Bob'.
    """
    # Arrange
    action = SimpleAction()
    params = SimpleAction.Params(name="  Bob  ")

    # Act
    result = await bench.run(action, params, rollup=False)

    # Assert
    assert result.greeting == "Hello, Bob!"


@pytest.mark.asyncio
async def test_simple_action_result_type(bench: TestBench) -> None:
    """
    SimpleAction возвращает экземпляр SimpleAction.Result.

    Проверяет, что результат — конкретный тип Result, а не BaseResult.
    """
    # Arrange
    action = SimpleAction()
    params = SimpleAction.Params(name="Charlie")

    # Act
    result = await bench.run(action, params, rollup=False)

    # Assert
    assert isinstance(result, SimpleAction.Result)
