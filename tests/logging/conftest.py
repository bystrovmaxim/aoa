"""
Фикстуры специфичные для тестов подсистемы логирования.
Доступны только в tests/logging/ и её подпапках.
"""

import pytest

from action_machine.Logging.console_logger import console_logger
from action_machine.Logging.expression_evaluator import expression_evaluator
from action_machine.Logging.log_coordinator import log_coordinator
from action_machine.Logging.log_scope import log_scope

# ======================================================================
# ФИКСТУРЫ ДЛЯ ТЕСТОВ ЛОГИРОВАНИЯ
# ======================================================================


@pytest.fixture
def evaluator() -> expression_evaluator:
    """
    Экземпляр вычислителя выражений для тестов iif.

    ExpressionEvaluator используется для:
    - Вычисления простых выражений
    - Обработки конструкций iif
    - Безопасного парсинга с вложенными кавычками
    """
    return expression_evaluator()


@pytest.fixture
def coordinator(recording_logger):  # recording_logger из корневого conftest
    """
    Координатор с одним логером-шпионом.

    Позволяет тестировать:
    - Рассылку сообщений
    - Подстановку переменных
    - Обработку ошибок
    """
    return log_coordinator(loggers=[recording_logger])


@pytest.fixture
def console_no_colors() -> console_logger:
    """
    Консольный логер без ANSI-цветов.

    Используется в тестах с capsys для проверки вывода
    без необходимости обрабатывать escape-последовательности.
    """
    return console_logger(use_colors=False)


@pytest.fixture
def console_with_colors() -> console_logger:
    """
    Консольный логер с ANSI-цветами.

    Используется для тестирования цветного вывода
    и проверки наличия ANSI-кодов в отформатированных строках.
    """
    return console_logger(use_colors=True)


@pytest.fixture
def complex_scope() -> log_scope:
    """
    Скоуп с несколькими уровнями вложенности.

    Пример: ProcessOrderAction.validate_user.before
    Используется для тестирования as_dotpath().
    """
    return log_scope(action="ProcessOrderAction", aspect="validate_user", event="before")


@pytest.fixture
def plugin_scope() -> log_scope:
    """
    Скоуп для тестирования плагинов.

    Пример: ProcessOrderAction.MetricsPlugin.global_finish
    """
    return log_scope(action="ProcessOrderAction", plugin="MetricsPlugin", event="global_finish")
