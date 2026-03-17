"""
Корневые фикстуры pytest — доступны во всех тестах автоматически.
Pytest подхватывает этот файл без явного импорта.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from action_machine.Context.Context import Context
from action_machine.Context.EnvironmentInfo import EnvironmentInfo
from action_machine.Context.RequestInfo import RequestInfo
from action_machine.Context.UserInfo import UserInfo
from action_machine.Core.BaseParams import BaseParams
from action_machine.Logging.BaseLogger import base_logger
from action_machine.Logging.LogScope import log_scope

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


class RecordingLogger(base_logger):
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
        scope: log_scope,
        message: str,
        var: dict[str, Any],
        context: Context,
        state: dict[str, Any],
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
                "context": context,
                "state": state.copy(),
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
def context() -> Context:
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
def scope() -> log_scope:
    """Стандартный тестовый скоуп с action, aspect и event."""
    return log_scope(action="TestAction", aspect="test", event="before")


@pytest.fixture
def simple_scope() -> log_scope:
    """Простой скоуп только с действием."""
    return log_scope(action="TestAction")


@pytest.fixture
def state() -> dict[str, Any]:
    """Пустое начальное состояние."""
    return {}


@pytest.fixture
def populated_state() -> dict[str, Any]:
    """
    Состояние с данными для тестов.

    Содержит:
    - total: общая сумма (float)
    - count: количество (int)
    - processed: флаг обработки (bool)
    - order: вложенный словарь с данными заказа
    """
    return {"total": 1500.0, "count": 42, "processed": True, "order": {"id": 12345, "status": "pending"}}


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
