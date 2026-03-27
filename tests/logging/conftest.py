# tests/logging/conftest.py
"""
Фикстуры для тестов подсистемы логирования.

Доступны только в tests/logging/ и её подпапках.
Предоставляют готовые экземпляры компонентов логирования
для использования в тестах: вычислитель выражений, координатор,
консольные логгеры и различные конфигурации LogScope.
"""

import pytest

from action_machine.logging.console_logger import ConsoleLogger
from action_machine.logging.expression_evaluator import ExpressionEvaluator
from action_machine.logging.log_coordinator import LogCoordinator
from action_machine.logging.log_scope import LogScope


@pytest.fixture
def evaluator() -> ExpressionEvaluator:
    """
    Экземпляр вычислителя выражений для тестов iif.

    ExpressionEvaluator используется для:
    - Вычисления простых выражений (арифметика, сравнения, логика).
    - Обработки конструкций iif(condition; true_branch; false_branch).
    - Безопасного парсинга с вложенными кавычками и скобками.
    - Вызова встроенных функций (len, upper, lower, format_number,
      цветовые функции, debug, exists).
    """
    return ExpressionEvaluator()


@pytest.fixture
def coordinator(recording_logger):  # recording_logger из корневого conftest
    """
    Координатор логирования с одним логером-шпионом.

    Позволяет тестировать:
    - Рассылку сообщений всем логгерам.
    - Подстановку переменных из разных namespace.
    - Обработку iif-конструкций.
    - Обработку ошибок в шаблонах.
    """
    return LogCoordinator(loggers=[recording_logger])


@pytest.fixture
def console_no_colors() -> ConsoleLogger:
    """
    Консольный логгер без ANSI-цветов.

    Используется в тестах с capsys для проверки вывода
    без необходимости обрабатывать escape-последовательности.
    """
    return ConsoleLogger(use_colors=False)


@pytest.fixture
def console_with_colors() -> ConsoleLogger:
    """
    Консольный логгер с ANSI-цветами.

    Используется для тестирования цветного вывода
    и проверки наличия ANSI-кодов в отформатированных строках.
    """
    return ConsoleLogger(use_colors=True)


@pytest.fixture
def complex_scope() -> LogScope:
    """
    Scope с несколькими уровнями вложенности.

    Результат as_dotpath(): "ProcessOrderAction.validate_user.before"
    Используется для тестирования формирования dotpath.
    """
    return LogScope(action="ProcessOrderAction", aspect="validate_user", event="before")


@pytest.fixture
def plugin_scope() -> LogScope:
    """
    Scope для тестирования плагинов.

    Результат as_dotpath(): "ProcessOrderAction.MetricsPlugin.global_finish"
    """
    return LogScope(action="ProcessOrderAction", plugin="MetricsPlugin", event="global_finish")
