# tests/model/test_base_schema_resolve.py
"""
Тесты BaseSchema.resolve() для dot-path навигации по вложенным объектам.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

BaseSchema.resolve("user.extra.org") обходит цепочку вложенных объектов,
выполняя один шаг навигации на каждом сегменте пути. На каждом шаге
выбирается стратегия навигации в зависимости от типа текущего объекта:

1. BaseSchema → __getitem__ (dict-подобный доступ через pydantic-поля).
2. dict → прямой доступ по ключу.
3. Любой другой объект → getattr.

Цепочка может содержать объекты разных типов: Context (BaseSchema) →
UserInfo (BaseSchema) → значение.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

Два уровня вложенности:
    - Context → UserInfo → user_id (BaseSchema → BaseSchema → значение).
    - Context → RequestInfo → trace_id (BaseSchema → BaseSchema → значение).

Три и более уровня:
    - Глубокая цепочка BaseSchema-объектов (3+ уровней).
    - BaseSchema → BaseSchema → BaseSchema → значение.

Смешанные типы в цепочке:
    - BaseSchema → dict → dict → значение (через BaseState extra-поля).
    - BaseSchema → BaseSchema → dict → значение.

Навигация по словарям (через BaseState extra="allow"):
    - Простой доступ к значению в extra-dict.
    - Вложенные словари (dict → dict → dict).
    - Получение целого dict как значения.
    - Получение списка из словаря.

Default при отсутствии промежуточного ключа:
    - Промежуточный BaseSchema не содержит поля → default.
    - Промежуточный dict не содержит ключа → default.
"""

from pydantic import ConfigDict

from action_machine.intents.context.context import Context
from action_machine.intents.context.request_info import RequestInfo
from action_machine.intents.context.runtime_info import RuntimeInfo
from action_machine.intents.context.user_info import UserInfo
from action_machine.model.base_schema import BaseSchema
from action_machine.model.base_state import BaseState
from tests.scenarios.domain_model.roles import AdminRole, AgentRole, UserRole

# ═════════════════════════════════════════════════════════════════════════════
# Вспомогательные классы
# ═════════════════════════════════════════════════════════════════════════════


class NestedSchema(BaseSchema):
    """
    Вспомогательная схема для создания произвольных цепочек вложенных
    BaseSchema-объектов. Используется для тестирования глубокой навигации.
    extra="allow" позволяет передавать произвольные поля через kwargs.
    """

    model_config = ConfigDict(frozen=True, extra="allow")


# ═════════════════════════════════════════════════════════════════════════════
# Два уровня вложенности
# ═════════════════════════════════════════════════════════════════════════════


class TestTwoLevels:
    """resolve через два уровня: объект → вложенный объект → значение."""

    def test_context_to_user_field(self) -> None:
        """
        resolve("user.user_id") — Context → UserInfo → user_id.

        Первый шаг: Context.__getitem__("user") → UserInfo.
        Второй шаг: UserInfo.__getitem__("user_id") → "agent_007".
        Оба объекта — BaseSchema, стратегия — __getitem__.
        """
        # Arrange
        user = UserInfo(user_id="agent_007", roles=(AgentRole,))
        ctx = Context(user=user)

        # Act
        result = ctx.resolve("user.user_id")

        # Assert
        assert result == "agent_007"

    def test_context_to_user_roles(self) -> None:
        """
        resolve("user.roles") — доступ к кортежу типов ролей через вложенность.
        """
        # Arrange
        user = UserInfo(user_id="42", roles=(AdminRole, UserRole))
        ctx = Context(user=user)

        # Act
        result = ctx.resolve("user.roles")

        # Assert
        assert result == (AdminRole, UserRole)

    def test_context_to_request_field(self) -> None:
        """
        resolve("request.trace_id") — Context → RequestInfo → trace_id.
        """
        # Arrange
        request = RequestInfo(trace_id="trace-abc-123", request_path="/api/v1/orders")
        ctx = Context(request=request)

        # Act
        result = ctx.resolve("request.trace_id")

        # Assert
        assert result == "trace-abc-123"

    def test_context_to_runtime_field(self) -> None:
        """
        resolve("runtime.hostname") — Context → RuntimeInfo → hostname.
        """
        # Arrange
        runtime = RuntimeInfo(hostname="pod-xyz-42", service_name="order-service")
        ctx = Context(runtime=runtime)

        # Act
        result = ctx.resolve("runtime.hostname")

        # Assert
        assert result == "pod-xyz-42"


# ═════════════════════════════════════════════════════════════════════════════
# Три и более уровня вложенности
# ═════════════════════════════════════════════════════════════════════════════


class TestThreeOrMoreLevels:
    """resolve через три и более уровней вложенности."""

    def test_deep_schema_chain(self) -> None:
        """
        resolve("level1.level2.level3.value") — цепочка из трёх
        вложенных BaseSchema-объектов до конечного значения.
        """
        # Arrange — три уровня вложенных NestedSchema
        level3 = NestedSchema(value="deep")
        level2 = NestedSchema(level3=level3)
        level1 = NestedSchema(level2=level2)
        root = NestedSchema(level1=level1)

        # Act
        result = root.resolve("level1.level2.level3.value")

        # Assert
        assert result == "deep"

    def test_deep_dict_nesting_via_state(self) -> None:
        """
        resolve("level1.level2.value") — BaseState → dict → dict → значение.

        BaseState с extra="allow" хранит произвольные значения,
        включая вложенные словари.
        """
        # Arrange — BaseState с глубоко вложенными словарями
        state = BaseState(level1={"level2": {"value": "deep"}})

        # Act
        result = state.resolve("level1.level2.value")

        # Assert
        assert result == "deep"

    def test_four_level_dict_chain(self) -> None:
        """
        resolve("a.b.c.d") — четыре уровня через dict-ы в BaseState.
        """
        # Arrange
        state = BaseState(a={"b": {"c": {"d": "found"}}})

        # Act
        result = state.resolve("a.b.c.d")

        # Assert
        assert result == "found"


# ═════════════════════════════════════════════════════════════════════════════
# Навигация по словарям
# ═════════════════════════════════════════════════════════════════════════════


class TestDictNavigation:
    """resolve через словари (dict) внутри BaseSchema-объектов."""

    def test_state_dict_simple_key(self) -> None:
        """
        resolve("data.key") — BaseState → dict → значение.
        """
        # Arrange
        state = BaseState(data={"key": "value"})

        # Act
        result = state.resolve("data.key")

        # Assert
        assert result == "value"

    def test_state_dict_nested_dicts(self) -> None:
        """
        resolve("data.nested.key") — dict → dict → значение.
        """
        # Arrange
        state = BaseState(data={"nested": {"key": "value"}})

        # Act
        result = state.resolve("data.nested.key")

        # Assert
        assert result == "value"

    def test_state_dict_multiple_keys(self) -> None:
        """
        Несколько независимых ключей в одном словаре — каждый
        доступен через отдельный resolve.
        """
        # Arrange
        state = BaseState(data={"a": 1, "b": 2, "c": 3})

        # Act & Assert
        assert state.resolve("data.a") == 1
        assert state.resolve("data.b") == 2
        assert state.resolve("data.c") == 3

    def test_state_dict_returns_list(self) -> None:
        """
        resolve возвращает список из словаря как единое значение.
        """
        # Arrange
        state = BaseState(data={"items": [1, 2, 3, 4]})

        # Act
        result = state.resolve("data.items")

        # Assert
        assert result == [1, 2, 3, 4]
        assert isinstance(result, list)

    def test_state_dict_returns_whole_dict(self) -> None:
        """
        resolve возвращает вложенный словарь целиком если путь
        заканчивается на ключе, чьё значение — dict.
        """
        # Arrange
        state = BaseState(data={"config": {"theme": "dark", "lang": "ru"}})

        # Act
        result = state.resolve("data.config")

        # Assert
        assert result == {"theme": "dark", "lang": "ru"}
        assert isinstance(result, dict)

    def test_state_dict_with_none_value(self) -> None:
        """
        Значение None в словаре — это валидное значение, не отсутствие.
        resolve возвращает None, а не default.
        """
        # Arrange
        state = BaseState(data={"key": None})

        # Act
        result = state.resolve("data.key")

        # Assert — None из словаря, не default
        assert result is None

    def test_state_empty_dict_returns_default(self) -> None:
        """
        resolve на пустом словаре по несуществующему ключу → default.
        """
        # Arrange
        state = BaseState(data={})

        # Act
        result = state.resolve("data.key", default="empty")

        # Assert
        assert result == "empty"


# ═════════════════════════════════════════════════════════════════════════════
# Смешанные типы в цепочке
# ═════════════════════════════════════════════════════════════════════════════


class TestMixedTypes:
    """resolve через смешанные типы: BaseSchema, dict, обычные объекты."""

    def test_schema_then_dict_then_dict(self) -> None:
        """
        BaseState → dict (settings) → dict (notifications) → значение.

        Стратегия навигации меняется: BaseSchema → dict → dict → значение.
        """
        # Arrange
        state = BaseState(
            settings={"theme": "dark", "notifications": {"email": True}},
        )

        # Act & Assert
        assert state.resolve("settings.theme") == "dark"
        assert state.resolve("settings.notifications.email") is True

    def test_context_schema_schema_value(self) -> None:
        """
        Context → UserInfo → user_id — чистая цепочка BaseSchema.
        """
        # Arrange
        ctx = Context(
            user=UserInfo(user_id="42"),
            request=RequestInfo(trace_id="abc"),
        )

        # Act & Assert
        assert ctx.resolve("user.user_id") == "42"
        assert ctx.resolve("request.trace_id") == "abc"

    def test_default_on_missing_intermediate_field(self) -> None:
        """
        Если промежуточное поле не найдено — resolve возвращает default,
        не бросая исключение. __getitem__ бросает KeyError, resolve
        ловит его и возвращает default.
        """
        # Arrange
        ctx = Context(user=UserInfo(user_id="42"))

        # Act — "nonexistent" нет среди полей UserInfo
        result = ctx.resolve("user.nonexistent.deep", default="N/A")

        # Assert
        assert result == "N/A"

    def test_default_on_missing_dict_key(self) -> None:
        """
        Промежуточный ключ не найден в словаре → default.
        """
        # Arrange
        state = BaseState(data={"existing": "value"})

        # Act — ключ "missing" не существует в dict
        result = state.resolve("data.missing.deep", default="not found")

        # Assert
        assert result == "not found"

    def test_default_on_completely_missing_path(self) -> None:
        """
        Первый сегмент пути не найден → default.
        """
        # Arrange
        state = BaseState(total=100)

        # Act
        result = state.resolve("nonexistent.deep.path", default="gone")

        # Assert
        assert result == "gone"

    def test_single_segment_resolve(self) -> None:
        """
        resolve с одним сегментом — эквивалент __getitem__.
        """
        # Arrange
        state = BaseState(total=100)

        # Act
        result = state.resolve("total")

        # Assert
        assert result == 100

    def test_single_segment_missing_returns_default(self) -> None:
        """
        resolve с одним несуществующим сегментом → default.
        """
        # Arrange
        state = BaseState(total=100)

        # Act
        result = state.resolve("missing", default=0)

        # Assert
        assert result == 0
