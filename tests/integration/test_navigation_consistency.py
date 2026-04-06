# tests/integration/test_navigation_consistency.py
"""
Интеграционный тест: консистентность навигации между BaseSchema.resolve()
и VariableSubstitutor.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Проверяет, что BaseSchema.resolve() и VariableSubstitutor дают
одинаковые результаты для одного и того же пути на одном и том же объекте.

Оба компонента делегируют навигацию единому DotPathNavigator [1].
Этот тест гарантирует, что рассинхронизация между ними невозможна
при будущих изменениях — именно такая рассинхронизация привела
к ошибке #1, когда resolve() использовал None как маркер отсутствия [2],
а VariableSubstitutor — _SENTINEL [4].

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

Строковое значение:
    resolve("user.user_id") == "test_user"
    substitute("{%context.user.user_id}") содержит "test_user"

Числовое значение:
    resolve("nested.count") == 42
    substitute("{%state.nested.count}") содержит "42"

None-значение (поле существует):
    resolve("optional_field") is None
    substitute("{%state.optional_field}") содержит "None" (не падает)

Отсутствующий путь:
    resolve("missing") возвращает default
    substitute("{%context.missing}") → LogTemplateError

Вложенный dict:
    resolve("data.key") == "value"
    substitute("{%var.data.key}") содержит "value"

Falsy-значения (0, False, ""):
    resolve возвращает falsy-значение, не default
    substitute содержит строковое представление falsy-значения
"""

from typing import Any

import pytest
from pydantic import ConfigDict, Field

from action_machine.context.context import Context
from action_machine.context.user_info import UserInfo
from action_machine.core.base_params import BaseParams
from action_machine.core.base_schema import BaseSchema
from action_machine.core.base_state import BaseState
from action_machine.core.exceptions import LogTemplateError
from action_machine.logging.log_scope import LogScope
from action_machine.logging.variable_substitutor import VariableSubstitutor
from action_machine.testing.stubs import ContextStub


# ─────────────────────────────────────────────────────────────────────────────
# Вспомогательные модели
# ─────────────────────────────────────────────────────────────────────────────

class _NullableSchema(BaseSchema):
    """Схема с nullable-полями для тестирования None-значений."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(description="Имя")
    optional_field: str | None = Field(default=None, description="Опциональное поле")


class _FalsySchema(BaseSchema):
    """Схема с falsy-значениями для тестирования 0, False, ''."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    zero_int: int = Field(description="Ноль")
    zero_float: float = Field(description="Ноль дробный")
    false_bool: bool = Field(description="Ложь")
    empty_str: str = Field(description="Пустая строка")


# ─────────────────────────────────────────────────────────────────────────────
# Общие фикстуры
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture()
def sub() -> VariableSubstitutor:
    """Свежий экземпляр VariableSubstitutor."""
    return VariableSubstitutor()


@pytest.fixture()
def scope() -> LogScope:
    """Минимальный LogScope."""
    return LogScope(machine="M", mode="test", action="A", aspect="a", nest_level=0)


@pytest.fixture()
def state() -> BaseState:
    """Пустой BaseState."""
    return BaseState()


@pytest.fixture()
def params() -> BaseParams:
    """Пустой BaseParams."""
    return BaseParams()


# ═════════════════════════════════════════════════════════════════════════════
# Строковые значения — resolve и substitutor дают одинаковый результат
# ═════════════════════════════════════════════════════════════════════════════

class TestStringValueConsistency:
    """Строковое значение: resolve() и substitutor согласованы."""

    def test_context_user_id(self, sub, scope, state, params) -> None:
        """resolve("user.user_id") и {%context.user.user_id} — один результат."""
        # Arrange
        ctx = ContextStub()

        # Act — через resolve
        result_resolve = ctx.resolve("user.user_id")

        # Act — через substitutor
        result_sub = sub.substitute(
            "{%context.user.user_id}", {}, scope, ctx, state, params
        )

        # Assert — оба возвращают одно и то же значение
        assert result_resolve == "test_user"
        assert result_resolve in result_sub

    def test_nested_schema_field(self, sub, scope, state, params) -> None:
        """Вложенное поле через BaseSchema — согласованность."""
        # Arrange
        ctx = ContextStub()

        # Act
        result_resolve = ctx.resolve("user.roles")
        result_sub = sub.substitute(
            "{%context.user.roles}", {}, scope, ctx, state, params
        )

        # Assert
        assert result_resolve is not None
        assert str(result_resolve) in result_sub


# ═════════════════════════════════════════════════════════════════════════════
# Числовые значения
# ═════════════════════════════════════════════════════════════════════════════

class TestNumericValueConsistency:
    """Числовое значение: resolve() и substitutor согласованы."""

    def test_state_numeric_field(self, sub, scope, ctx_stub, params) -> None:
        """Числовое поле в state — одинаковый результат."""
        # Arrange
        st = BaseState(count=42)

        # Act
        result_resolve = st.resolve("count")
        result_sub = sub.substitute("{%state.count}", {}, scope, ctx_stub, st, params)

        # Assert
        assert result_resolve == 42
        assert "42" in result_sub

    @pytest.fixture()
    def ctx_stub(self) -> Context:
        return ContextStub()


# ═════════════════════════════════════════════════════════════════════════════
# None-значения — ключевой сценарий (ошибка #1)
# ═════════════════════════════════════════════════════════════════════════════

class TestNoneValueConsistency:
    """None как значение поля: resolve() и substitutor согласованы [7]."""

    def test_none_field_resolve_returns_none(self) -> None:
        """resolve() для поля с None возвращает None, а не default."""
        # Arrange
        schema = _NullableSchema(name="Alice", optional_field=None)

        # Act
        result = schema.resolve("optional_field", default="fallback")

        # Assert — None это валидное значение, не отсутствие
        assert result is None

    def test_none_field_substitutor_returns_none_string(
        self, sub, scope, state, params
    ) -> None:
        """substitutor для поля с None выводит 'None', не падает."""
        # Arrange
        st = BaseState(optional_field=None)

        # Act
        result = sub.substitute(
            "{%state.optional_field}", {}, scope, ContextStub(), st, params
        )

        # Assert — substitutor преобразует None в строку "None"
        assert "None" in result

    def test_none_consistency_between_resolve_and_substitutor(
        self, sub, scope, params
    ) -> None:
        """resolve() возвращает None, substitutor выводит str(None) — согласовано."""
        # Arrange
        st = BaseState(value=None)

        # Act
        result_resolve = st.resolve("value")
        result_sub = sub.substitute(
            "{%state.value}", {}, scope, ContextStub(), st, params
        )

        # Assert
        assert result_resolve is None
        assert str(result_resolve) in result_sub


# ═════════════════════════════════════════════════════════════════════════════
# Отсутствующий путь — resolve возвращает default, substitutor бросает ошибку
# ═════════════════════════════════════════════════════════════════════════════

class TestMissingPathBehavior:
    """Отсутствующий путь: разное поведение — и это корректно."""

    def test_resolve_returns_default_for_missing(self) -> None:
        """resolve() для несуществующего пути возвращает default [7]."""
        # Arrange
        ctx = ContextStub()

        # Act
        result = ctx.resolve("user.nonexistent", default="MISSING")

        # Assert
        assert result == "MISSING"

    def test_substitutor_raises_for_missing(self, sub, scope, state, params) -> None:
        """substitutor для несуществующего пути бросает LogTemplateError [4]."""
        # Arrange
        ctx = ContextStub()

        # Act & Assert — строгая политика ошибок
        with pytest.raises(LogTemplateError, match="not found"):
            sub.substitute(
                "{%context.user.nonexistent}", {}, scope, ctx, state, params
            )


# ═════════════════════════════════════════════════════════════════════════════
# Вложенные dict — навигация через DotPathNavigator
# ═════════════════════════════════════════════════════════════════════════════

class TestNestedDictConsistency:
    """Вложенный dict: resolve() и substitutor через один навигатор."""

    def test_var_nested_dict(self, sub, scope, state, params) -> None:
        """Трёхуровневый dict — оба пути дают одинаковый результат."""
        # Arrange
        data: dict[str, Any] = {"a": {"b": {"c": "deep"}}}

        # Act — через substitutor (var namespace — dict)
        result_sub = sub.substitute(
            "{%var.a.b.c}", data, scope, ContextStub(), state, params
        )

        # Assert
        assert "deep" in result_sub

    def test_state_with_nested_dict(self, sub, scope, params) -> None:
        """BaseState с вложенным dict — resolve и substitutor согласованы."""
        # Arrange
        st = BaseState(nested={"key": "value"})

        # Act
        result_resolve = st.resolve("nested.key")
        result_sub = sub.substitute(
            "{%state.nested.key}", {}, scope, ContextStub(), st, params
        )

        # Assert
        assert result_resolve == "value"
        assert "value" in result_sub


# ═════════════════════════════════════════════════════════════════════════════
# Falsy-значения — 0, False, "" не подменяются на default
# ═════════════════════════════════════════════════════════════════════════════

class TestFalsyValueConsistency:
    """Falsy-значения: resolve() и substitutor не путают с отсутствием [8]."""

    def test_zero_int(self, sub, scope, params) -> None:
        """Значение 0 — валидное, не отсутствие."""
        # Arrange
        st = BaseState(count=0)

        # Act
        result_resolve = st.resolve("count", default="MISSING")
        result_sub = sub.substitute(
            "{%state.count}", {}, scope, ContextStub(), st, params
        )

        # Assert
        assert result_resolve == 0
        assert "0" in result_sub

    def test_false_bool(self, sub, scope, params) -> None:
        """Значение False — валидное, не отсутствие."""
        # Arrange
        st = BaseState(flag=False)

        # Act
        result_resolve = st.resolve("flag", default="MISSING")
        result_sub = sub.substitute(
            "{%state.flag}", {}, scope, ContextStub(), st, params
        )

        # Assert
        assert result_resolve is False
        assert "False" in result_sub

    def test_empty_string(self, sub, scope, params) -> None:
        """Значение '' — валидное, не отсутствие."""
        # Arrange
        st = BaseState(label="")

        # Act
        result_resolve = st.resolve("label", default="MISSING")
        result_sub = sub.substitute(
            "{%state.label}", {}, scope, ContextStub(), st, params
        )

        # Assert
        assert result_resolve == ""
        assert result_sub is not None


# ═════════════════════════════════════════════════════════════════════════════
# LogScope — навигация через duck-typed __getitem__
# ═════════════════════════════════════════════════════════════════════════════

class TestLogScopeConsistency:
    """LogScope: substitutor корректно навигирует через __getitem__ [3]."""

    def test_scope_field_via_substitutor(self, sub, state, params) -> None:
        """Поле scope доступно через {%scope.action}."""
        # Arrange
        sc = LogScope(
            machine="TestMachine", mode="test",
            action="MyAction", aspect="my_aspect", nest_level=0,
        )

        # Act
        result = sub.substitute(
            "{%scope.action}", {}, sc, ContextStub(), state, params
        )

        # Assert
        assert "MyAction" in result

    def test_scope_field_via_getitem(self) -> None:
        """LogScope["action"] возвращает то же значение."""
        # Arrange
        sc = LogScope(action="MyAction")

        # Act & Assert
        assert sc["action"] == "MyAction"