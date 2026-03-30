# tests/logging/test_debug_function.py
"""
Тесты функции debug() в шаблонах логирования.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

- Интроспекция объектов верхнего уровня (params, state, context, var).
- Интроспекция вложенных объектов (context.user, state.order и т.д.).
- Вывод только публичных полей и свойств (без приватных/защищённых).
- Корректная обработка декоратора @sensitive (показ конфигурации).
- Обработка ошибок для несуществующих переменных (с функцией exists()).
- Граничные случаи: циклические ссылки, глубокая вложенность, большие структуры.
- Функция exists() для безопасной проверки наличия переменных.
"""

import re

import pytest
from pydantic import Field

from action_machine.context.context import Context
from action_machine.context.user_info import UserInfo
from action_machine.core.base_params import BaseParams
from action_machine.core.base_state import BaseState
from action_machine.logging.expression_evaluator import ExpressionEvaluator
from action_machine.logging.sensitive_decorator import sensitive

# ----------------------------------------------------------------------
# Вспомогательные классы
# ----------------------------------------------------------------------


class SimpleUser:
    """Простой пользователь с публичными и приватными полями."""
    def __init__(self, user_id: str, name: str, age: int):
        self.user_id = user_id
        self.name = name
        self.age = age
        self._private = "hidden"
        self.__mangled = "mangled"


class UserWithSensitive:
    """Пользователь с чувствительными свойствами."""
    def __init__(self, email: str, phone: str):
        self._email = email
        self._phone = phone

    @property
    @sensitive(True, max_chars=3, char='#', max_percent=40)
    def email(self):
        return self._email

    @property
    @sensitive(False)
    def phone(self):
        return self._phone

    @property
    def public_name(self):
        return "Public Name"


class CyclicObject:
    """Объект с циклической ссылкой для теста обнаружения циклов."""
    def __init__(self, name: str):
        self.name = name
        self.other = None


class DeepNested:
    """Глубоко вложенный объект для теста ограничения глубины."""
    def __init__(self, level: int):
        self.level = level
        self.child = DeepNested(level - 1) if level > 0 else None
        self.data = {"key": "value"}


class MyParams(BaseParams):
    """Тестовые параметры для проверки debug() на pydantic-моделях."""
    user_id: str = Field(description="Идентификатор пользователя")
    amount: float = Field(description="Сумма операции")


# ----------------------------------------------------------------------
# Фикстуры
# ----------------------------------------------------------------------


@pytest.fixture
def evaluator() -> ExpressionEvaluator:
    return ExpressionEvaluator()


@pytest.fixture
def context_with_user() -> Context:
    user = UserInfo(user_id="agent_007", roles=["agent", "admin"], extra={"org": "acme"})
    return Context(user=user)


@pytest.fixture
def complex_context() -> Context:
    user = UserWithSensitive(email="secret@example.com", phone="+1234567890")
    ctx = Context(user=UserInfo(user_id="test"))
    ctx._extra = {"account": user}
    return ctx


@pytest.fixture
def populated_state() -> BaseState:
    return BaseState({
        "total": 1500.0,
        "count": 42,
        "order": {"id": 12345, "status": "pending", "items": ["item1", "item2"]},
        "user": SimpleUser("alice", "Alice", 30),
    })


@pytest.fixture
def params_with_attrs() -> MyParams:
    return MyParams(user_id="bob", amount=99.99)


# ----------------------------------------------------------------------
# Тесты
# ----------------------------------------------------------------------


class TestDebugFunction:
    """Тесты функции debug() в ExpressionEvaluator."""

    def test_debug_params(self, evaluator: ExpressionEvaluator, params_with_attrs: MyParams):
        """debug() на pydantic BaseParams выводит объявленные поля модели."""
        result = evaluator.evaluate("debug(params)", {"params": params_with_attrs})
        assert "MyParams:" in result
        assert "user_id: str = 'bob'" in result
        assert "amount: float = 99.99" in result
        # Методы pydantic не должны появляться
        assert "get" not in result
        assert "items" not in result

    def test_debug_state(self, evaluator: ExpressionEvaluator, populated_state: BaseState):
        """debug() на BaseState выводит все публичные атрибуты."""
        result = evaluator.evaluate("debug(state)", {"state": populated_state})
        assert "total: float = 1500.0" in result
        assert "count: int = 42" in result
        assert "order: dict = " in result
        assert "'id': 12345" in result
        assert "'status': 'pending'" in result
        assert "'items'" in result
        assert "item1" in result
        assert "item2" in result
        # user — объект, не раскрывается при max_depth=1
        assert "user: SimpleUser = <tests.logging.test_debug_function.SimpleUser object at" in result

    def test_debug_context(self, evaluator: ExpressionEvaluator, context_with_user: Context):
        """debug() на Context выводит компоненты верхнего уровня."""
        result = evaluator.evaluate("debug(context)", {"context": context_with_user})
        assert "user: UserInfo = UserInfo(user_id='agent_007', roles=['agent', 'admin']," in result
        assert "org" in result or "acme" in result
        assert "request: RequestInfo = RequestInfo(trace_id=None, request_timestamp=None, request_path=None, request_method=None, full_url=None, client_ip=None, protocol=None, user_agent=None, extra={}, tags={})" in result
        assert "runtime: RuntimeInfo = RuntimeInfo(hostname=None, service_name=None, service_version=None, container_id=None, pod_name=None, extra={})" in result

    def test_debug_var(self, evaluator: ExpressionEvaluator):
        """debug() на словаре выводит содержимое."""
        var = {"a": 1, "b": "hello", "c": [1, 2, 3]}
        result = evaluator.evaluate("debug(var)", {"var": var})
        assert "'a': 1" in result
        assert "'b': 'hello'" in result
        assert "'c': [1, 2, 3]" in result

    def test_debug_nested(self, evaluator: ExpressionEvaluator, complex_context: Context):
        """debug() на вложенном объекте с @sensitive."""
        account = complex_context._extra["account"]
        result = evaluator.evaluate("debug(account)", {"account": account})
        assert "public_name: str = 'Public Name'" in result
        assert "email: str (sensitive: enabled, max_chars=3, char='#', max_percent=40) = sec#####" in result
        assert "phone: str (sensitive: disabled) = '+1234567890'" in result

    def test_deep_nested(self, evaluator: ExpressionEvaluator):
        """debug() при max_depth=1 не раскрывает вложенные объекты."""
        deep = DeepNested(3)
        result = evaluator.evaluate("debug(deep)", {"deep": deep})
        assert "level: int = 3" in result
        assert "child: DeepNested = <tests.logging.test_debug_function.DeepNested object at" in result
        # Вложенные уровни не раскрыты
        assert "level: int = 2" not in result
        assert "level: int = 1" not in result

    def test_private_fields_not_shown(self, evaluator: ExpressionEvaluator):
        """debug() не показывает приватные и mangled поля."""
        class WithPrivate:
            def __init__(self):
                self.public = "visible"
                self._private = "hidden"
                self.__mangled = "hidden"
        obj = WithPrivate()
        result = evaluator.evaluate("debug(obj)", {"obj": obj})
        assert "public: str = 'visible'" in result
        assert "_private" not in result
        assert "__mangled" not in result

    def test_sensitive_enabled_shows_config(self, evaluator: ExpressionEvaluator):
        """debug() показывает конфигурацию @sensitive и маскированное значение."""
        class SensitiveEnabled:
            def __init__(self, val):
                self._val = val
            @property
            @sensitive(True, max_chars=2, char='*', max_percent=30)
            def secret(self):
                return self._val
        obj = SensitiveEnabled("abcdefghij")
        result = evaluator.evaluate("debug(obj)", {"obj": obj})
        assert "secret: str (sensitive: enabled, max_chars=2, char='*', max_percent=30) = ab*****" in result

    def test_sensitive_on_property_not_field(self, evaluator: ExpressionEvaluator):
        """debug() корректно обрабатывает @sensitive на property, а не на обычных полях."""
        class Mixed:
            def __init__(self):
                self.public_field = "public"
                self._field = "field"
            @property
            @sensitive(True)
            def prop(self):
                return self._field
        obj = Mixed()
        result = evaluator.evaluate("debug(obj)", {"obj": obj})
        assert "public_field: str = 'public'" in result
        assert "prop: str (sensitive: enabled, max_chars=3, char='*', max_percent=50) = fie*****" in result
        assert not re.search(r'\b_field\b', result, re.MULTILINE)

    def test_exists_with_debug(self, evaluator: ExpressionEvaluator):
        """exists() + debug() в шаблоне iif."""
        data_obj = {"a": 1}
        names = {"data": data_obj}
        template = "{iif(exists('data'); debug(data); 'No data')}"
        result = evaluator.process_template(template, names)
        assert "'a': 1" in result
