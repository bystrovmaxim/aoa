"""
Корневые фикстуры pytest — доступны во всех тестах автоматически.
Pytest подхватывает этот файл без явного импорта.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from action_machine.Context.context import Context
from action_machine.Context.environment_info import EnvironmentInfo
from action_machine.Context.request_info import RequestInfo
from action_machine.Context.user_info import UserInfo
from action_machine.Core.BaseParams import BaseParams
from action_machine.Core.BaseState import BaseState
from action_machine.Logging.base_logger import BaseLogger
from action_machine.Logging.log_scope import LogScope

# ======================================================================
# ТЕСТОВЫЕ МОДЕЛИ ДАННЫХ
# ======================================================================

@dataclass(frozen=True)
class ParamsTest(BaseParams):
    """
    Стандартные тестовые параметры для всех тестов.
    Содержит типичные поля, используемые в примерах:
    - user_id: идентификатор пользователя
    - card_token: токен карты (строка)
    - amount: сумма (float)
    - success: флаг успеха (bool)
    """
    user_id: int = 42
    card_token: str = "tok_test_abc"
    amount: float = 1500.0
    success: bool = True


class RecordingLogger(BaseLogger):
    """
    Логер-шпион — записывает все сообщения в список records.
    Используется для проверки:
    - Что координатор правильно рассылает сообщения
    - Что фильтрация работает
    - Что подстановка переменных выполняется
    Не выводит ничего в консоль — только накапливает записи.
    Атрибуты:
        records: список словарей с параметрами каждого вызова write
    """

    def __init__(self, filters: list[str] | None = None) -> None:
        """Создаёт логер-шпион с опциональными фильтрами."""
        super().__init__(filters=filters)
        self.records: list[dict[str, Any]] = []

    async def write(
        self,
        scope: LogScope,
        message: str,
        var: dict[str, Any],
        ctx: Context,
        state: BaseState,
        params: BaseParams,
        indent: int,
    ) -> None:
        """
        Записывает сообщение в records.
        Вызывается только если фильтры прошли.
        Сохраняет все параметры для последующей проверки в тестах.
        """
        self.records.append(
            {
                "scope": scope,
                "message": message,
                "var": var.copy(),
                "ctx": ctx,
                "state": state.to_dict(),
                "params": params,
                "indent": indent,
            }
        )

    def clear(self) -> None:
        """Очищает историю записей (полезно между тестами)."""
        self.records.clear()


# ======================================================================
# БАЗОВЫЕ ФИКСТУРЫ
# ======================================================================

@pytest.fixture
def params() -> ParamsTest:
    """Стандартные тестовые параметры."""
    return ParamsTest()


@pytest.fixture
def context_fixture() -> Context:
    """
    Стандартный тестовый контекст.
    Содержит:
    - Пользователя с ролями ['user', 'admin'] и extra {'org': 'acme'}
    - Информацию о запросе с trace_id, путем и методом
    - Информацию об окружении с hostname, service_name
    """
    user = UserInfo(
        user_id="agent_1",
        roles=["user", "admin"],
        extra={"org": "acme"},
    )
    request = RequestInfo(
        trace_id="trace-abc-123",
        request_path="/api/v1/orders",
        request_method="POST",
        client_ip="192.168.1.1",
        user_agent="pytest/1.0",
    )
    environment = EnvironmentInfo(
        hostname="pod-xyz-42",
        service_name="order-service",
        service_version="1.2.3",
        environment="test",
    )
    return Context(user=user, request=request, environment=environment)


@pytest.fixture
def empty_context() -> Context:
    """Пустой контекст для тестов, где не нужны данные."""
    return Context()


@pytest.fixture
def recording_logger() -> RecordingLogger:
    """Логер-шпион без фильтров (принимает всё)."""
    return RecordingLogger()


@pytest.fixture
def filtered_logger() -> RecordingLogger:
    """Логер-шпион с фильтром 'TestAction'."""
    return RecordingLogger(filters=[r"TestAction"])


@pytest.fixture
def scope() -> LogScope:
    """Стандартный тестовый скоуп с action, aspect и event."""
    return LogScope(action="TestAction", aspect="test", event="before")


@pytest.fixture
def simple_scope() -> LogScope:
    """Простой скоуп только с действием."""
    return LogScope(action="TestAction")


@pytest.fixture
def state() -> BaseState:
    """Пустое начальное состояние."""
    return BaseState()


@pytest.fixture
def populated_state() -> BaseState:
    """
    Состояние с данными для тестов.
    Содержит:
    - total: общая сумма (float)
    - count: количество (int)
    - processed: флаг обработки (bool)
    - order: вложенный словарь с данными заказа
    """
    return BaseState({
        "total": 1500.0,
        "count": 42,
        "processed": True,
        "order": {"id": 12345, "status": "pending"},
    })


# ======================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ======================================================================

def make_context(
    user_id: str = "agent_1",
    roles: list[str] | None = None,
    trace_id: str = "trace-abc-123",
) -> Context:
    """
    Создаёт тестовый контекст с пользователем и запросом.
    Аргументы:
        user_id: идентификатор пользователя.
        roles: список ролей.
        trace_id: идентификатор трассировки.
    Возвращает:
        Готовый Context для использования в тестах.
    """
    user = UserInfo(
        user_id=user_id,
        roles=roles or ["user", "admin"],
        extra={"org": "acme"},
    )
    request = RequestInfo(
        trace_id=trace_id,
        request_path="/api/v1/orders",
        request_method="POST",
    )
    environment = EnvironmentInfo(
        hostname="pod-xyz-42",
        service_name="order-service",
        environment="production",
    )
    return Context(user=user, request=request, environment=environment)


def create_context_with_user(user_id: str, roles: list[str] | None = None) -> Context:
    """
    Создаёт контекст с конкретным пользователем.
    Аргументы:
        user_id: идентификатор пользователя
        roles: список ролей (по умолчанию пустой)
    Возвращает:
        Context с указанным пользователем
    """
    return Context(
        user=UserInfo(user_id=user_id, roles=roles or []),
        request=RequestInfo(),
        environment=EnvironmentInfo(),
    )