# tests/logging/test_debug_filter.py
"""
Тесты фильтра |debug в шаблонах логирования.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

- Базовое использование: {%var.obj|debug} выводит интроспекцию объекта.
- Вывод содержит публичные поля и свойства, типы и значения.
- Маскирование чувствительных данных (@sensitive) сохраняется.
- Вложенные объекты НЕ раскрываются (max_depth=1).
- Работает внутри и вне блоков iif.
- Работает со всеми namespace (var, state, context, params, scope).
"""

import pytest
from pydantic import Field

from action_machine.context.context import Context
from action_machine.context.user_info import UserInfo
from action_machine.core.base_params import BaseParams
from action_machine.core.base_state import BaseState
from action_machine.logging.expression_evaluator import ExpressionEvaluator
from action_machine.logging.log_scope import LogScope
from action_machine.logging.sensitive_decorator import sensitive
from action_machine.logging.variable_substitutor import VariableSubstitutor

# ----------------------------------------------------------------------
# Вспомогательные классы
# ----------------------------------------------------------------------


class SimpleObj:
    """Простой объект с публичными и приватным полями."""
    def __init__(self):
        self.name = "Simple"
        self.value = 42
        self._private = "hidden"


class UserWithSensitive:
    """Класс с чувствительным свойством."""
    def __init__(self, email: str, phone: str):
        self._email = email
        self._phone = phone

    @property
    @sensitive(True, max_chars=3, char='#', max_percent=50)
    def email(self):
        return self._email

    @property
    @sensitive(False)
    def phone(self):
        return self._phone

    @property
    def public_name(self):
        return "Public Name"


class DeepObj:
    """Объект с вложенной структурой для проверки отсутствия рекурсии."""
    def __init__(self):
        self.level1 = "visible"
        self.child = self.Child()

    class Child:
        def __init__(self):
            self.level2 = "hidden"


# ----------------------------------------------------------------------
# Фикстуры
# ----------------------------------------------------------------------


@pytest.fixture
def substitutor():
    return VariableSubstitutor()


@pytest.fixture
def empty_scope():
    return LogScope()


@pytest.fixture
def empty_context():
    return Context()


@pytest.fixture
def empty_state():
    return BaseState()


@pytest.fixture
def empty_params():
    return BaseParams()


@pytest.fixture
def evaluator():
    """ExpressionEvaluator для тестов, требующих прямого вычисления iif."""
    return ExpressionEvaluator()


# ----------------------------------------------------------------------
# Тесты
# ----------------------------------------------------------------------


class TestDebugFilter:
    """Тесты фильтра |debug."""

    def test_debug_filter_on_simple_object(self, substitutor, empty_scope, empty_context, empty_state, empty_params):
        """Базовый тест: фильтр debug выводит публичные поля."""
        obj = SimpleObj()
        var = {"obj": obj}
        template = "{%var.obj|debug}"
        result = substitutor.substitute(
            template, var=var, scope=empty_scope, ctx=empty_context,
            state=empty_state, params=empty_params
        )
        assert "SimpleObj:" in result
        assert "name: str = 'Simple'" in result
        assert "value: int = 42" in result
        assert "_private" not in result

    def test_debug_filter_on_dict(self, substitutor, empty_scope, empty_context, empty_state, empty_params):
        """Фильтр debug на словаре."""
        data = {"a": 1, "b": 2, "c": {"nested": "value"}}
        var = {"data": data}
        template = "{%var.data|debug}"
        result = substitutor.substitute(
            template, var=var, scope=empty_scope, ctx=empty_context,
            state=empty_state, params=empty_params
        )
        assert "dict:" in result
        assert "'a': 1" in result
        assert "'b': 2" in result
        assert "'c': {'nested': 'value'}" in result

    def test_debug_filter_on_sensitive_property(self, substitutor, empty_scope, empty_context, empty_state, empty_params):
        """Фильтр debug учитывает декоратор @sensitive."""
        user = UserWithSensitive("secret@example.com", "+1234567890")
        var = {"user": user}
        template = "{%var.user|debug}"
        result = substitutor.substitute(
            template, var=var, scope=empty_scope, ctx=empty_context,
            state=empty_state, params=empty_params
        )
        assert "email: str (sensitive: enabled, max_chars=3, char='#', max_percent=50) = sec#####" in result
        assert "phone: str (sensitive: disabled) = '+1234567890'" in result
        assert "public_name: str = 'Public Name'" in result

    def test_debug_filter_no_recursion(self, substitutor, empty_scope, empty_context, empty_state, empty_params):
        """Фильтр debug не раскрывает вложенные объекты (max_depth=1)."""
        obj = DeepObj()
        var = {"obj": obj}
        template = "{%var.obj|debug}"
        result = substitutor.substitute(
            template, var=var, scope=empty_scope, ctx=empty_context,
            state=empty_state, params=empty_params
        )
        assert "DeepObj:" in result
        assert "level1: str = 'visible'" in result
        assert "child: Child = <tests.logging.test_debug_filter.DeepObj.Child object at" in result
        assert "level2" not in result

    def test_debug_filter_inside_iif(self, substitutor, empty_scope, empty_context, empty_state, empty_params):
        """Фильтр debug работает внутри выражений iif."""
        obj = SimpleObj()
        var = {"obj": obj}
        template = "{iif(1==1; {%var.obj|debug}; '')}"
        result = substitutor.substitute(
            template, var=var, scope=empty_scope, ctx=empty_context,
            state=empty_state, params=empty_params
        )
        assert "SimpleObj:" in result
        assert "name: str = 'Simple'" in result

    def test_debug_filter_with_exists(self, evaluator):
        """Совместное использование exists и debug."""
        obj = SimpleObj()
        names = {"obj": obj}
        template = "{iif(exists('obj'); debug(obj); 'No object')}"
        result = evaluator.process_template(template, names)
        assert "SimpleObj:" in result

        result2 = evaluator.process_template(template, {})
        assert result2 == "No object"

    def test_debug_filter_on_context_object(self, substitutor, empty_scope, empty_state, empty_params):
        """Фильтр debug работает с namespace context."""
        user = UserInfo(user_id="test_user", roles=["user"], extra={"org": "acme"})
        ctx = Context(user=user)
        template = "{%context.user|debug}"
        result = substitutor.substitute(
            template, var={}, scope=empty_scope, ctx=ctx,
            state=empty_state, params=empty_params
        )
        assert "UserInfo:" in result
        assert "user_id: str = 'test_user'" in result
        assert "roles: list = ['user']" in result
        assert "extra: dict = {'org': 'acme'}" in result

    def test_debug_filter_on_state(self, substitutor, empty_scope, empty_context, empty_params):
        """Фильтр debug работает с namespace state."""
        state = BaseState({"total": 100, "items": [1, 2, 3]})
        template = "{%state|debug}"
        result = substitutor.substitute(
            template, var={}, scope=empty_scope, ctx=empty_context,
            state=state, params=empty_params
        )
        assert "total: int = 100" in result
        assert "items: list = [1, 2, 3]" in result

    def test_debug_filter_on_params(self, substitutor, empty_scope, empty_context, empty_state):
        """Фильтр debug работает с namespace params (pydantic BaseParams)."""

        class MyParams(BaseParams):
            param1: str = Field(default="hello", description="Первый параметр")
            param2: int = Field(default=42, description="Второй параметр")

        params = MyParams()
        template = "{%params|debug}"
        result = substitutor.substitute(
            template, var={}, scope=empty_scope, ctx=empty_context,
            state=empty_state, params=params
        )
        assert "MyParams:" in result
        assert "param1: str = 'hello'" in result
        assert "param2: int = 42" in result

    def test_debug_filter_on_scope(self, substitutor, empty_context, empty_state, empty_params):
        """Фильтр debug работает с namespace scope."""
        scope = LogScope(machine="TestMachine", mode="test", action="TestAction", aspect="test")
        template = "{%scope|debug}"
        result = substitutor.substitute(
            template, var={}, scope=scope, ctx=empty_context,
            state=empty_state, params=empty_params
        )
        assert "machine: str = 'TestMachine'" in result
        assert "mode: str = 'test'" in result
        assert "action: str = 'TestAction'" in result
        assert "aspect: str = 'test'" in result

    def test_debug_filter_on_missing_object_raises(self, substitutor, empty_scope, empty_context, empty_state, empty_params):
        """Обращение к несуществующей переменной с |debug → LogTemplateError."""
        var = {"obj": "some"}
        template = "{%var.missing|debug}"
        with pytest.raises(Exception) as exc_info:
            substitutor.substitute(
                template, var=var, scope=empty_scope, ctx=empty_context,
                state=empty_state, params=empty_params
            )
        assert "not found" in str(exc_info.value) or "LogTemplateError" in str(exc_info.value)

    def test_debug_filter_on_none_value(self, substitutor, empty_scope, empty_context, empty_state, empty_params):
        """Фильтр debug на None выводит 'NoneType = None'."""
        var = {"nothing": None}
        template = "{%var.nothing|debug}"
        result = substitutor.substitute(
            template, var=var, scope=empty_scope, ctx=empty_context,
            state=empty_state, params=empty_params
        )
        assert "NoneType = None" in result
