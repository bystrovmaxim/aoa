# tests2/logging/test_debug_filter.py
"""
Тесты фильтра |debug в шаблонах логирования.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Фильтр |debug выводит форматированную интроспекцию объекта: его публичные поля,
типы, значения и конфигурацию @sensitive. Используется для отладки в логах:
{%var.obj|debug}, {%state|debug}, {%context.user|debug}.

Фильтр |debug — это сокращение для функции debug(), которая определена
в ExpressionEvaluator и вызывает _inspect_object с max_depth=1 (только
непосредственные поля). Вложенные объекты не раскрываются, чтобы не
засорять логи.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

- Базовое использование: {%var.obj|debug} выводит интроспекцию объекта.
- Вывод содержит публичные поля и свойства, типы и значения.
- Маскирование чувствительных данных (@sensitive) сохраняется.
- Вложенные объекты НЕ раскрываются (max_depth=1).
- Работает внутри и вне блоков iif.
- Работает со всеми namespace (var, state, context, params, scope).
- Обработка None, пустых коллекций, циклических ссылок.
"""

import pytest

from action_machine.context.context import Context
from action_machine.context.user_info import UserInfo
from action_machine.core.base_params import BaseParams
from action_machine.core.base_state import BaseState
from action_machine.logging.expression_evaluator import ExpressionEvaluator
from action_machine.logging.log_scope import LogScope
from action_machine.logging.sensitive_decorator import sensitive
from action_machine.logging.variable_substitutor import VariableSubstitutor


# ======================================================================
# Вспомогательные классы
# ======================================================================

class SimpleObj:
    """Простой объект с публичными и приватными полями."""
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


class CyclicObj:
    """Объект с циклической ссылкой."""
    def __init__(self, name: str):
        self.name = name
        self.other = None


# ======================================================================
# Фикстуры
# ======================================================================

@pytest.fixture
def substitutor() -> VariableSubstitutor:
    return VariableSubstitutor()


@pytest.fixture
def evaluator() -> ExpressionEvaluator:
    return ExpressionEvaluator()


@pytest.fixture
def empty_scope() -> LogScope:
    return LogScope()


@pytest.fixture
def empty_context() -> Context:
    return Context()


@pytest.fixture
def empty_state() -> BaseState:
    return BaseState()


@pytest.fixture
def empty_params() -> BaseParams:
    return BaseParams()


# ======================================================================
# ТЕСТЫ: Базовое использование |debug
# ======================================================================

class TestDebugFilterBasic:
    """Фильтр |debug выводит интроспекцию объекта."""

    def test_debug_on_simple_object(
        self, substitutor: VariableSubstitutor,
        empty_scope: LogScope, empty_context: Context,
        empty_state: BaseState, empty_params: BaseParams,
    ) -> None:
        """{%var.obj|debug} выводит публичные поля SimpleObj."""
        obj = SimpleObj()
        var = {"obj": obj}
        result = substitutor.substitute(
            "{%var.obj|debug}",
            var, empty_scope, empty_context, empty_state, empty_params,
        )
        assert "SimpleObj:" in result
        assert "name: str = 'Simple'" in result
        assert "value: int = 42" in result
        assert "_private" not in result

    def test_debug_on_dict(
        self, substitutor: VariableSubstitutor,
        empty_scope: LogScope, empty_context: Context,
        empty_state: BaseState, empty_params: BaseParams,
    ) -> None:
        """{%var.data|debug} на словаре выводит содержимое."""
        data = {"a": 1, "b": 2, "c": {"nested": "value"}}
        result = substitutor.substitute(
            "{%var.data|debug}",
            {"data": data}, empty_scope, empty_context, empty_state, empty_params,
        )
        assert "dict:" in result
        assert "'a': 1" in result
        assert "'b': 2" in result
        assert "'c': {'nested': 'value'}" in result

    def test_debug_on_sensitive_property(
        self, substitutor: VariableSubstitutor,
        empty_scope: LogScope, empty_context: Context,
        empty_state: BaseState, empty_params: BaseParams,
    ) -> None:
        """Фильтр |debug учитывает декоратор @sensitive."""
        user = UserWithSensitive("secret@example.com", "+1234567890")
        result = substitutor.substitute(
            "{%var.user|debug}",
            {"user": user}, empty_scope, empty_context, empty_state, empty_params,
        )
        assert "email: str (sensitive: enabled, max_chars=3, char='#', max_percent=50) = sec#####" in result
        assert "phone: str (sensitive: disabled) = '+1234567890'" in result
        assert "public_name: str = 'Public Name'" in result

    def test_debug_no_recursion(
        self, substitutor: VariableSubstitutor,
        empty_scope: LogScope, empty_context: Context,
        empty_state: BaseState, empty_params: BaseParams,
    ) -> None:
        """Фильтр |debug не раскрывает вложенные объекты (max_depth=1)."""
        obj = DeepObj()
        result = substitutor.substitute(
            "{%var.obj|debug}",
            {"obj": obj}, empty_scope, empty_context, empty_state, empty_params,
        )
        assert "DeepObj:" in result
        assert "level1: str = 'visible'" in result
        assert "child: Child = <tests.logging.test_debug_filter.DeepObj.Child object at" in result
        assert "level2" not in result


# ======================================================================
# ТЕСТЫ: |debug с разными namespace
# ======================================================================

class TestDebugNamespaces:
    """Фильтр |debug работает со всеми namespace."""

    def test_debug_on_context(
        self, substitutor: VariableSubstitutor,
        empty_scope: LogScope, empty_state: BaseState, empty_params: BaseParams,
    ) -> None:
        """{%context.user|debug} — интроспекция UserInfo из контекста."""
        user = UserInfo(user_id="test_user", roles=["user"], extra={"org": "acme"})
        ctx = Context(user=user)
        result = substitutor.substitute(
            "{%context.user|debug}",
            {}, empty_scope, ctx, empty_state, empty_params,
        )
        assert "UserInfo:" in result
        assert "user_id: str = 'test_user'" in result
        assert "roles: list = ['user']" in result
        assert "extra: dict = {'org': 'acme'}" in result

    def test_debug_on_state(
        self, substitutor: VariableSubstitutor,
        empty_scope: LogScope, empty_context: Context, empty_params: BaseParams,
    ) -> None:
        """{%state|debug} — интроспекция BaseState."""
        state = BaseState({"total": 100, "items": [1, 2, 3]})
        result = substitutor.substitute(
            "{%state|debug}",
            {}, empty_scope, empty_context, state, empty_params,
        )
        assert "total: int = 100" in result
        assert "items: list = [1, 2, 3]" in result

    def test_debug_on_params(
        self, substitutor: VariableSubstitutor,
        empty_scope: LogScope, empty_context: Context, empty_state: BaseState,
    ) -> None:
        """{%params|debug} — интроспекция pydantic-модели."""
        class MyParams(BaseParams):
            param1: str
            param2: int

        params = MyParams(param1="hello", param2=42)
        result = substitutor.substitute(
            "{%params|debug}",
            {}, empty_scope, empty_context, empty_state, params,
        )
        assert "MyParams:" in result
        assert "param1: str = 'hello'" in result
        assert "param2: int = 42" in result

    def test_debug_on_scope(
        self, substitutor: VariableSubstitutor,
        empty_context: Context, empty_state: BaseState, empty_params: BaseParams,
    ) -> None:
        """{%scope|debug} — интроспекция LogScope."""
        scope = LogScope(machine="TestMachine", mode="test", action="TestAction", aspect="test")
        result = substitutor.substitute(
            "{%scope|debug}",
            {}, scope, empty_context, empty_state, empty_params,
        )
        assert "machine: str = 'TestMachine'" in result
        assert "mode: str = 'test'" in result
        assert "action: str = 'TestAction'" in result
        assert "aspect: str = 'test'" in result


# ======================================================================
# ТЕСТЫ: |debug внутри iif
# ======================================================================

class TestDebugInsideIif:
    """Фильтр |debug работает внутри iif."""

    def test_debug_filter_inside_iif(
        self, substitutor: VariableSubstitutor,
        empty_scope: LogScope, empty_context: Context,
        empty_state: BaseState, empty_params: BaseParams,
    ) -> None:
        """{iif(1==1; {%var.obj|debug}; '')} — debug выполняется."""
        obj = SimpleObj()
        template = "{iif(1==1; {%var.obj|debug}; '')}"
        result = substitutor.substitute(
            template, {"obj": obj}, empty_scope, empty_context, empty_state, empty_params,
        )
        assert "SimpleObj:" in result
        assert "name: str = 'Simple'" in result

    def test_debug_with_exists(
        self, evaluator: ExpressionEvaluator,
    ) -> None:
        """exists() и debug() в iif — безопасная интроспекция."""
        obj = SimpleObj()
        template = "{iif(exists('obj'); debug(obj); 'No object')}"
        result = evaluator.process_template(template, {"obj": obj})
        assert "SimpleObj:" in result

        result2 = evaluator.process_template(template, {})
        assert result2 == "No object"


# ======================================================================
# ТЕСТЫ: Граничные случаи
# ======================================================================

class TestDebugEdgeCases:
    """Обработка None, пустых объектов, циклов."""

    def test_debug_on_none(
        self, substitutor: VariableSubstitutor,
        empty_scope: LogScope, empty_context: Context,
        empty_state: BaseState, empty_params: BaseParams,
    ) -> None:
        """{%var.nothing|debug} на None выводит 'NoneType = None'."""
        result = substitutor.substitute(
            "{%var.nothing|debug}",
            {"nothing": None}, empty_scope, empty_context, empty_state, empty_params,
        )
        assert "NoneType = None" in result

    def test_debug_on_empty_list(
        self, substitutor: VariableSubstitutor,
        empty_scope: LogScope, empty_context: Context,
        empty_state: BaseState, empty_params: BaseParams,
    ) -> None:
        """Пустой список выводит 'list[]'."""
        result = substitutor.substitute(
            "{%var.empty|debug}",
            {"empty": []}, empty_scope, empty_context, empty_state, empty_params,
        )
        assert "list[]" in result

    def test_debug_on_empty_dict(
        self, substitutor: VariableSubstitutor,
        empty_scope: LogScope, empty_context: Context,
        empty_state: BaseState, empty_params: BaseParams,
    ) -> None:
        """Пустой словарь выводит 'dict{}'."""
        result = substitutor.substitute(
            "{%var.empty|debug}",
            {"empty": {}}, empty_scope, empty_context, empty_state, empty_params,
        )
        assert "dict{}" in result

    def test_debug_on_cyclic_reference(
        self, substitutor: VariableSubstitutor,
        empty_scope: LogScope, empty_context: Context,
        empty_state: BaseState, empty_params: BaseParams,
    ) -> None:
        """Циклическая ссылка помечается <cycle detected>."""
        a = CyclicObj("A")
        b = CyclicObj("B")
        a.other = b
        b.other = a
        result = substitutor.substitute(
            "{%var.a|debug}",
            {"a": a}, empty_scope, empty_context, empty_state, empty_params,
        )
        assert "<cycle detected>" in result