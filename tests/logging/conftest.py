"""
Фикстуры специфичные для тестов подсистемы логирования.
Доступны только в tests/logging/ и её подпапках.
"""

import pytest

from action_machine.Logging.console_logger import ConsoleLogger
from action_machine.Logging.expression_evaluator import ExpressionEvaluator
from action_machine.Logging.log_coordinator import LogCoordinator
from action_machine.Logging.log_scope import LogScope

# ======================================================================
# ФИКСТУРЫ ДЛЯ ТЕСТОВ ЛОГИРОВАНИЯ
# ======================================================================


@pytest.fixture
def evaluator() -> ExpressionEvaluator:
    """
    Экземпляр вычислителя выражений для тестов iif.

    ExpressionEvaluator используется для:
    - Вычисления простых выражений
    - Обработки конструкций iif
    - Безопасного парсинга с вложенными кавычками
    """
    return ExpressionEvaluator()


@pytest.fixture
def coordinator(recording_logger):  # recording_logger из корневого conftest
    """
    Координатор с одним логером-шпионом.

    Позволяет тестировать:
    - Рассылку сообщений
    - Подстановку переменных
    - Обработку ошибок
    """
    return LogCoordinator(loggers=[recording_logger])


@pytest.fixture
def console_no_colors() -> ConsoleLogger:
    """
    Консольный логер без ANSI-цветов.

    Используется в тестах с capsys для проверки вывода
    без необходимости обрабатывать escape-последовательности.
    """
    return ConsoleLogger(use_colors=False)


@pytest.fixture
def console_with_colors() -> ConsoleLogger:
    """
    Консольный логер с ANSI-цветами.

    Используется для тестирования цветного вывода
    и проверки наличия ANSI-кодов в отформатированных строках.
    """
    return ConsoleLogger(use_colors=True)


@pytest.fixture
def complex_scope() -> LogScope:
    """
    Скоуп с несколькими уровнями вложенности.

    Пример: ProcessOrderAction.validate_user.before
    Используется для тестирования as_dotpath().
    """
    return LogScope(action="ProcessOrderAction", aspect="validate_user", event="before")


@pytest.fixture
def plugin_scope() -> LogScope:
    """
    Скоуп для тестирования плагинов.

    Пример: ProcessOrderAction.MetricsPlugin.global_finish
    """
    return LogScope(action="ProcessOrderAction", plugin="MetricsPlugin", event="global_finish")
