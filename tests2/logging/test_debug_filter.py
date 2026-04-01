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
- Обработка None, пустых коллекций.

═══════════════════════════════════════════════════════════════════════════════
ОБНАРУЖЕНИЕ ЦИКЛОВ
═══════════════════════════════════════════════════════════════════════════════

Циклические ссылки обнаруживаются через множество visited (id объектов).
При max_depth=1 (значение по умолчанию для debug()) цикл A→B→A
обнаруживается только на уровне самоссылки (A.self_ref = A), потому что
B не раскрывается рекурсивно и его поля не проверяются. Для обнаружения
циклов через промежуточные объекты (A→B→A) нужен max_depth >= 2.

Тест test_debug_on_self_reference проверяет прямую самоссылку (max_depth=1).
Тест test_debug_on_indirect_cycle проверяет непрямой цикл (max_depth=2)
через _inspect_object напрямую.
"""

import pytest

from action_machine.context.context import Context
from action_machine.context.user_info import UserInfo
from action_machine.core.base_params import BaseParams
from action_machine.core.base_state import BaseState
from action_machine.logging.expression_evaluator import ExpressionEvaluator, _inspect_object
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


class SelfRefObj:
    """Объект с прямой самоссылкой — цикл длины 1."""
    def __init__(self, name: str):
        self.name = name
        self.self_ref = self


class CyclicObj:
    """Объект для построения непрямого цикла A→B→A."""
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
        # Arrange — простой объект с публичными и приватными полями
        obj = SimpleObj()
        var = {"obj": obj}

        # Act — подстановка шаблона с фильтром |debug
        result = substitutor.substitute(
            "{%var.obj|debug}",
            var, empty_scope, empty_context, empty_state, empty_params,
        )

        # Assert — публичные поля видны, приватные скрыты
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
        # Arrange — словарь с вложенными данными
        data = {"a": 1, "b": 2, "c": {"nested": "value"}}

        # Act
        result = substitutor.substitute(
            "{%var.data|debug}",
            {"data": data}, empty_scope, empty_context, empty_state, empty_params,
        )

        # Assert — ключи и значения видны
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
        # Arrange — объект с чувствительным и отключённым @sensitive свойствами
        user = UserWithSensitive("secret@example.com", "+1234567890")

        # Act
        result = substitutor.substitute(
            "{%var.user|debug}",
            {"user": user}, empty_scope, empty_context, empty_state, empty_params,
        )

        # Assert — email замаскирован, phone показан как есть (sensitive: disabled)
        assert "email: str (sensitive: enabled, max_chars=3, char='#', max_percent=50) = sec#####" in result
        assert "phone: str (sensitive: disabled) = '+1234567890'" in result
        assert "public_name: str = 'Public Name'" in result

    def test_debug_no_recursion(
        self, substitutor: VariableSubstitutor,
        empty_scope: LogScope, empty_context: Context,
        empty_state: BaseState, empty_params: BaseParams,
    ) -> None:
        """
        Фильтр |debug не раскрывает вложенные объекты (max_depth=1).
        Вложенный Child показывается как repr(value) — строка с адресом объекта.
        Поля вложенного объекта (level2) не видны.
        """
        # Arrange — объект с вложенной структурой
        obj = DeepObj()

        # Act
        result = substitutor.substitute(
            "{%var.obj|debug}",
            {"obj": obj}, empty_scope, empty_context, empty_state, empty_params,
        )

        # Assert — первый уровень виден, вложенный объект не раскрыт
        assert "DeepObj:" in result
        assert "level1: str = 'visible'" in result
        # Вложенный объект показан как repr — содержит имя класса.
        # Проверяем только имя класса, без полного пути модуля,
        # потому что путь зависит от расположения тестов (tests/ vs tests2/).
        assert "child: Child" in result
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
        # Arrange — контекст с пользователем и extra-данными
        user = UserInfo(user_id="test_user", roles=["user"], extra={"org": "acme"})
        ctx = Context(user=user)

        # Act
        result = substitutor.substitute(
            "{%context.user|debug}",
            {}, empty_scope, ctx, empty_state, empty_params,
        )

        # Assert — поля UserInfo видны
        assert "UserInfo:" in result
        assert "user_id: str = 'test_user'" in result
        assert "roles: list = ['user']" in result
        assert "extra: dict = {'org': 'acme'}" in result

    def test_debug_on_state(
        self, substitutor: VariableSubstitutor,
        empty_scope: LogScope, empty_context: Context, empty_params: BaseParams,
    ) -> None:
        """{%state|debug} — интроспекция BaseState."""
        # Arrange — состояние с числом и списком
        state = BaseState({"total": 100, "items": [1, 2, 3]})

        # Act
        result = substitutor.substitute(
            "{%state|debug}",
            {}, empty_scope, empty_context, state, empty_params,
        )

        # Assert — поля состояния видны
        assert "total: int = 100" in result
        assert "items: list = [1, 2, 3]" in result

    def test_debug_on_params(
        self, substitutor: VariableSubstitutor,
        empty_scope: LogScope, empty_context: Context, empty_state: BaseState,
    ) -> None:
        """{%params|debug} — интроспекция pydantic-модели."""
        # Arrange — pydantic-модель с полями
        class MyParams(BaseParams):
            param1: str
            param2: int

        params = MyParams(param1="hello", param2=42)

        # Act
        result = substitutor.substitute(
            "{%params|debug}",
            {}, empty_scope, empty_context, empty_state, params,
        )

        # Assert — поля pydantic-модели видны
        assert "MyParams:" in result
        assert "param1: str = 'hello'" in result
        assert "param2: int = 42" in result

    def test_debug_on_scope(
        self, substitutor: VariableSubstitutor,
        empty_context: Context, empty_state: BaseState, empty_params: BaseParams,
    ) -> None:
        """{%scope|debug} — интроспекция LogScope."""
        # Arrange — scope с несколькими полями
        scope = LogScope(machine="TestMachine", mode="test", action="TestAction", aspect="test")

        # Act
        result = substitutor.substitute(
            "{%scope|debug}",
            {}, scope, empty_context, empty_state, empty_params,
        )

        # Assert — поля scope видны
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
        # Arrange
        obj = SimpleObj()
        template = "{iif(1==1; {%var.obj|debug}; '')}"

        # Act
        result = substitutor.substitute(
            template, {"obj": obj}, empty_scope, empty_context, empty_state, empty_params,
        )

        # Assert — debug вывод присутствует
        assert "SimpleObj:" in result
        assert "name: str = 'Simple'" in result

    def test_debug_with_exists(
        self, evaluator: ExpressionEvaluator,
    ) -> None:
        """exists() и debug() в iif — безопасная интроспекция."""
        # Arrange — объект есть в контексте
        obj = SimpleObj()
        template = "{iif(exists('obj'); debug(obj); 'No object')}"

        # Act — объект есть
        result = evaluator.process_template(template, {"obj": obj})

        # Assert
        assert "SimpleObj:" in result

        # Act — объекта нет
        result2 = evaluator.process_template(template, {})

        # Assert
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
        # Arrange & Act
        result = substitutor.substitute(
            "{%var.nothing|debug}",
            {"nothing": None}, empty_scope, empty_context, empty_state, empty_params,
        )

        # Assert
        assert "NoneType = None" in result

    def test_debug_on_empty_list(
        self, substitutor: VariableSubstitutor,
        empty_scope: LogScope, empty_context: Context,
        empty_state: BaseState, empty_params: BaseParams,
    ) -> None:
        """Пустой список выводит 'list[]'."""
        # Arrange & Act
        result = substitutor.substitute(
            "{%var.empty|debug}",
            {"empty": []}, empty_scope, empty_context, empty_state, empty_params,
        )

        # Assert
        assert "list[]" in result

    def test_debug_on_empty_dict(
        self, substitutor: VariableSubstitutor,
        empty_scope: LogScope, empty_context: Context,
        empty_state: BaseState, empty_params: BaseParams,
    ) -> None:
        """Пустой словарь выводит 'dict{}'."""
        # Arrange & Act
        result = substitutor.substitute(
            "{%var.empty|debug}",
            {"empty": {}}, empty_scope, empty_context, empty_state, empty_params,
        )

        # Assert
        assert "dict{}" in result

    def test_debug_on_self_reference(
        self, substitutor: VariableSubstitutor,
        empty_scope: LogScope, empty_context: Context,
        empty_state: BaseState, empty_params: BaseParams,
    ) -> None:
        """
        Прямая самоссылка (obj.self_ref = obj) обнаруживается при max_depth=1.

        Объект добавляет свой id в visited при входе в _inspect_object.
        Когда _format_field_line обрабатывает поле self_ref, id(self_ref)
        совпадает с id(obj) (это один и тот же объект), и поле помечается
        <cycle detected>.
        """
        # Arrange — объект ссылается сам на себя
        obj = SelfRefObj("A")

        # Act
        result = substitutor.substitute(
            "{%var.obj|debug}",
            {"obj": obj}, empty_scope, empty_context, empty_state, empty_params,
        )

        # Assert — самоссылка обнаружена
        assert "SelfRefObj:" in result
        assert "name: str = 'A'" in result
        assert "<cycle detected>" in result

    def test_debug_on_indirect_cycle(self) -> None:
        """
        Непрямой цикл A→B→A обнаруживается при max_depth=2.

        При max_depth=1 (debug по умолчанию) объект B показывается как
        repr(value), и его поля не проверяются — цикл не виден.
        При max_depth=2 _inspect_object заходит внутрь B, обнаруживает
        B.other=A, и id(A) уже в visited → <cycle detected>.
        """
        # Arrange — два объекта, ссылающихся друг на друга
        a = CyclicObj("A")
        b = CyclicObj("B")
        a.other = b
        b.other = a

        # Act — max_depth=2 для обнаружения непрямого цикла
        result = _inspect_object(a, max_depth=2)

        # Assert — цикл обнаружен на втором уровне
        assert "CyclicObj:" in result
        assert "name: str = 'A'" in result
        assert "<cycle detected>" in result
