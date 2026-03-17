"""
Общие фикстуры для тестирования core-компонентов.
"""

from dataclasses import dataclass

import pytest

from action_machine.Context.Context import Context
from action_machine.Context.EnvironmentInfo import environment_info
from action_machine.Context.RequestInfo import request_info
from action_machine.Context.UserInfo import user_info
from action_machine.Core.ReadableMixin import ReadableMixin

# ======================================================================
# ТЕСТОВЫЕ КЛАССЫ ДЛЯ ReadableMixin
# ======================================================================


class SimpleReadable(ReadableMixin):
    """
    Простой класс для тестирования ReadableMixin.

    Позволяет создавать объекты с произвольными атрибутами.
    """

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class NestedReadable(ReadableMixin):
    """
    Класс с вложенными Readable-объектами для тестирования resolve.

    Используется для создания глубоких цепочек объектов.
    """

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


@dataclass
class FlatData(ReadableMixin):
    """Плоская структура данных для тестов."""

    name: str = "test"
    value: int = 42
    active: bool = True


@dataclass
class NestedData(ReadableMixin):
    """Вложенная структура данных для тестов."""

    id: int = 123
    data: dict = None

    def __post_init__(self):
        if self.data is None:
            self.data = {"key": "value", "number": 999}


# ======================================================================
# ФИКСТУРЫ С ПРОСТЫМИ ОБЪЕКТАМИ
# ======================================================================


@pytest.fixture
def flat_user():
    """Пользователь с плоскими полями (без вложенности)."""
    return user_info(user_id="42", roles=["admin", "user"])


@pytest.fixture
def simple_readable():
    """Простой объект с ReadableMixin для тестов."""
    return SimpleReadable(name="test", value=42, active=True, tags=["a", "b", "c"])


# ======================================================================
# ФИКСТУРЫ С ВЛОЖЕННЫМИ ОБЪЕКТАМИ
# ======================================================================


@pytest.fixture
def user_with_extra():
    """Пользователь с extra-словарём."""
    return user_info(user_id="42", roles=["admin"], extra={"org": "acme", "level": {"floor": 5}})


@pytest.fixture
def context_with_user():
    """Контекст с пользователем."""
    user = user_info(user_id="agent_007", roles=["agent"], extra={"clearance": "top"})
    return Context(user=user)


@pytest.fixture
def nested_readable():
    """Объект с вложенной структурой для тестирования resolve."""
    inner = NestedReadable(id=123, data={"key": "value", "number": 999})
    return SimpleReadable(name="root", child=inner, items=[1, 2, 3])


@pytest.fixture
def deep_nested():
    """Глубоко вложенная структура (3+ уровня)."""
    level3 = SimpleReadable(value="deep")
    level2 = SimpleReadable(level3=level3)
    level1 = SimpleReadable(level2=level2)
    return SimpleReadable(level1=level1)


# ======================================================================
# ФИКСТУРЫ ДЛЯ ТЕСТИРОВАНИЯ ОТСУТСТВИЯ КЛЮЧЕЙ
# ======================================================================


@pytest.fixture
def user_without_extra():
    """Пользователь без extra-словаря."""
    return user_info(user_id="42")


# ======================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ======================================================================


def make_context_with_user(user_id: str = "agent_1") -> Context:
    """
    Создаёт контекст с пользователем для тестов.

    Аргументы:
        user_id: идентификатор пользователя

    Возвращает:
        Context с указанным пользователем
    """
    user = user_info(user_id=user_id, roles=["user", "admin"], extra={"org": "acme"})
    request = request_info(trace_id="trace-abc-123", request_path="/api/v1/orders", request_method="POST")
    environment = environment_info(hostname="pod-xyz-42", service_name="order-service", environment="production")
    return Context(user=user, request=request, environment=environment)
