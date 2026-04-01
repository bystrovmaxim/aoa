# tests/core/test_resolve_nested.py
"""
Тесты ReadableMixin.resolve() для вложенных объектов и словарей.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

resolve("user.extra.org") обходит цепочку вложенных объектов, выполняя
один шаг навигации (_resolve_one_step) на каждом сегменте пути. На каждом
шаге выбирается стратегия навигации в зависимости от типа текущего объекта:

1. ReadableMixin → _resolve_step_readable → __getitem__ → getattr.
2. dict → _resolve_step_dict → dict[segment].
3. Любой другой → _resolve_step_generic → getattr.

Цепочка может содержать объекты разных типов: Context (ReadableMixin) →
UserInfo (ReadableMixin) → extra (dict) → вложенный dict → значение.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

Два уровня вложенности:
    - Context → UserInfo → user_id (ReadableMixin → ReadableMixin → значение).
    - UserInfo → extra → ключ (ReadableMixin → dict → значение).

Три и более уровня:
    - Context → UserInfo → extra → вложенный dict → значение.
    - Глубокая цепочка ReadableMixin-объектов (3+ уровней).

Смешанные типы в цепочке:
    - ReadableMixin → dict → dict → значение.
    - dict → ReadableMixin → dict → значение.

Навигация по словарям:
    - Простой доступ к значению в dict.
    - Вложенные словари (dict → dict → dict).
    - Получение целого dict как значения.
    - Получение списка из словаря.

Default при отсутствии промежуточного ключа:
    - Промежуточный ReadableMixin не содержит атрибута → default.
    - Промежуточный dict не содержит ключа → default.
"""

from action_machine.context.context import Context
from action_machine.context.request_info import RequestInfo
from action_machine.context.runtime_info import RuntimeInfo
from action_machine.context.user_info import UserInfo
from action_machine.core.readable_mixin import ReadableMixin

# ═════════════════════════════════════════════════════════════════════════════
# Вспомогательные классы
# ═════════════════════════════════════════════════════════════════════════════


class SimpleReadable(ReadableMixin):
    """
    Вспомогательный класс для создания произвольных цепочек
    вложенных ReadableMixin-объектов. Каждый kwargs-аргумент
    становится атрибутом экземпляра.
    """

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


# ═════════════════════════════════════════════════════════════════════════════
# Два уровня вложенности
# ═════════════════════════════════════════════════════════════════════════════


class TestTwoLevels:
    """resolve через два уровня: объект → вложенный объект → значение."""

    def test_context_to_user_field(self) -> None:
        """
        resolve("user.user_id") — Context → UserInfo → user_id.

        Первый шаг: _resolve_one_step(Context, "user") → ctx.user (UserInfo).
        Второй шаг: _resolve_one_step(UserInfo, "user_id") → "agent_007".
        Оба объекта наследуют ReadableMixin → стратегия _resolve_step_readable.
        """
        # Arrange — Context с UserInfo внутри, имитация реального
        # контекста выполнения, создаваемого AuthCoordinator
        user = UserInfo(user_id="agent_007", roles=["agent"])
        ctx = Context(user=user)

        # Act — resolve по двухсегментному пути "user.user_id"
        result = ctx.resolve("user.user_id")

        # Assert — значение из вложенного UserInfo
        assert result == "agent_007"

    def test_context_to_user_roles(self) -> None:
        """
        resolve("user.roles") — доступ к полю-списку через вложенность.
        """
        # Arrange — UserInfo с двумя ролями
        user = UserInfo(user_id="42", roles=["admin", "user"])
        ctx = Context(user=user)

        # Act — resolve проходит Context → UserInfo → roles
        result = ctx.resolve("user.roles")

        # Assert — список ролей целиком
        assert result == ["admin", "user"]

    def test_user_extra_dict_value(self) -> None:
        """
        resolve("extra.org") — UserInfo → extra (dict) → значение.

        Первый шаг: _resolve_one_step(UserInfo, "extra") → dict.
        Второй шаг: _resolve_one_step(dict, "org") → _resolve_step_dict
        → dict["org"] → "acme".
        """
        # Arrange — UserInfo с extra-словарём
        user = UserInfo(user_id="42", extra={"org": "acme", "level": 5})

        # Act — resolve переключается с ReadableMixin на dict-стратегию
        result = user.resolve("extra.org")

        # Assert — значение из extra-словаря
        assert result == "acme"

    def test_context_to_request_field(self) -> None:
        """
        resolve("request.trace_id") — Context → RequestInfo → trace_id.

        RequestInfo — dataclass с ReadableMixin. Путь проходит через
        два ReadableMixin-объекта.
        """
        # Arrange — Context с RequestInfo
        request = RequestInfo(trace_id="trace-abc-123", request_path="/api/v1/orders")
        ctx = Context(request=request)

        # Act — resolve через два ReadableMixin
        result = ctx.resolve("request.trace_id")

        # Assert — trace_id из RequestInfo
        assert result == "trace-abc-123"

    def test_context_to_runtime_field(self) -> None:
        """
        resolve("runtime.hostname") — Context → RuntimeInfo → hostname.
        """
        # Arrange — Context с RuntimeInfo
        runtime = RuntimeInfo(hostname="pod-xyz-42", service_name="order-service")
        ctx = Context(runtime=runtime)

        # Act — resolve через RuntimeInfo
        result = ctx.resolve("runtime.hostname")

        # Assert — hostname из RuntimeInfo
        assert result == "pod-xyz-42"


# ═════════════════════════════════════════════════════════════════════════════
# Три и более уровня вложенности
# ═════════════════════════════════════════════════════════════════════════════


class TestThreeOrMoreLevels:
    """resolve через три и более уровней вложенности."""

    def test_context_user_extra_nested(self) -> None:
        """
        resolve("user.extra.org") — Context → UserInfo → extra (dict) → значение.

        Три шага: ReadableMixin → ReadableMixin → dict → значение.
        """
        # Arrange — Context с UserInfo, у которого extra содержит org
        user = UserInfo(user_id="42", extra={"org": "acme"})
        ctx = Context(user=user)

        # Act — resolve по трёхсегментному пути
        result = ctx.resolve("user.extra.org")

        # Assert — значение из вложенного словаря extra
        assert result == "acme"

    def test_deep_dict_nesting(self) -> None:
        """
        resolve("extra.level1.level2.value") — UserInfo → extra →
        dict → dict → значение. Четыре шага навигации.
        """
        # Arrange — UserInfo с глубоко вложенными словарями
        user = UserInfo(
            user_id="42",
            extra={"level1": {"level2": {"value": "deep"}}},
        )

        # Act — resolve проходит через три уровня dict-ов
        result = user.resolve("extra.level1.level2.value")

        # Assert — значение из самого глубокого уровня
        assert result == "deep"

    def test_deep_readable_chain(self) -> None:
        """
        resolve("level1.level2.level3.value") — цепочка из трёх
        вложенных ReadableMixin-объектов до конечного значения.
        """
        # Arrange — три уровня вложенных SimpleReadable
        level3 = SimpleReadable(value="deep")
        level2 = SimpleReadable(level3=level3)
        level1 = SimpleReadable(level2=level2)
        root = SimpleReadable(level1=level1)

        # Act — resolve по четырёхсегментному пути через ReadableMixin
        result = root.resolve("level1.level2.level3.value")

        # Assert — значение из самого глубокого объекта
        assert result == "deep"

    def test_four_levels_through_context(self) -> None:
        """
        resolve("user.extra.next.extra.data") — длинная цепочка
        через Context → UserInfo → extra (dict) → UserInfo → extra → значение.
        """
        # Arrange — UserInfo, вложенный в extra другого UserInfo
        inner_user = UserInfo(user_id="inner", extra={"data": "found_it"})
        outer_user = UserInfo(user_id="outer", extra={"next": inner_user})
        ctx = Context(user=outer_user)

        # Act — resolve переключается между ReadableMixin и dict несколько раз
        result = ctx.resolve("user.extra.next.extra.data")

        # Assert — значение из самого глубокого вложения
        assert result == "found_it"


# ═════════════════════════════════════════════════════════════════════════════
# Навигация по словарям
# ═════════════════════════════════════════════════════════════════════════════


class TestDictNavigation:
    """resolve через словари (dict) внутри ReadableMixin-объектов."""

    def test_dict_simple_key(self) -> None:
        """
        resolve("extra.key") — ReadableMixin → dict → значение.
        """
        # Arrange — UserInfo с simple dict в extra
        user = UserInfo(extra={"key": "value"})

        # Act — resolve через dict
        result = user.resolve("extra.key")

        # Assert — значение из словаря
        assert result == "value"

    def test_dict_nested_dicts(self) -> None:
        """
        resolve("extra.nested.key") — dict → dict → значение.
        """
        # Arrange — вложенные словари в extra
        user = UserInfo(extra={"nested": {"key": "value"}})

        # Act — два шага по словарям
        result = user.resolve("extra.nested.key")

        # Assert — значение из вложенного словаря
        assert result == "value"

    def test_dict_multiple_keys(self) -> None:
        """
        Несколько независимых ключей в одном словаре — каждый
        доступен через отдельный resolve.
        """
        # Arrange — словарь с тремя ключами
        user = UserInfo(extra={"a": 1, "b": 2, "c": 3})

        # Act & Assert — каждый ключ возвращает своё значение
        assert user.resolve("extra.a") == 1
        assert user.resolve("extra.b") == 2
        assert user.resolve("extra.c") == 3

    def test_dict_returns_list(self) -> None:
        """
        resolve возвращает список из словаря как единое значение.
        """
        # Arrange — список как значение ключа в словаре
        user = UserInfo(extra={"items": [1, 2, 3, 4]})

        # Act — resolve возвращает весь список
        result = user.resolve("extra.items")

        # Assert — список целиком, тип сохранён
        assert result == [1, 2, 3, 4]
        assert isinstance(result, list)

    def test_dict_returns_whole_dict(self) -> None:
        """
        resolve возвращает вложенный словарь целиком если путь
        заканчивается на ключе, чьё значение — dict.
        """
        # Arrange — dict как значение ключа
        user = UserInfo(extra={"config": {"theme": "dark", "lang": "ru"}})

        # Act — resolve до уровня config, не глубже
        result = user.resolve("extra.config")

        # Assert — весь вложенный словарь
        assert result == {"theme": "dark", "lang": "ru"}
        assert isinstance(result, dict)

    def test_dict_with_none_value(self) -> None:
        """
        Значение None в словаре — это валидное значение, не отсутствие.

        resolve возвращает None, а не default. Аналогично поведению
        для None в атрибутах ReadableMixin (test_resolve_flat.py).
        """
        # Arrange — ключ со значением None
        user = UserInfo(extra={"key": None})

        # Act — resolve находит ключ, его значение — None
        result = user.resolve("extra.key")

        # Assert — None из словаря, не default
        assert result is None

    def test_dict_empty_returns_default(self) -> None:
        """
        resolve на пустом словаре по несуществующему ключу → default.
        """
        # Arrange — пустой extra
        user = UserInfo(extra={})

        # Act — ключ "key" не существует в пустом словаре
        result = user.resolve("extra.key", default="empty")

        # Assert — вернулся default
        assert result == "empty"


# ═════════════════════════════════════════════════════════════════════════════
# Смешанные типы в цепочке
# ═════════════════════════════════════════════════════════════════════════════


class TestMixedTypes:
    """resolve через смешанные типы: ReadableMixin, dict, обычные объекты."""

    def test_readable_then_dict_then_dict(self) -> None:
        """
        Context → UserInfo (ReadableMixin) → extra (dict) →
        settings (dict) → theme (str).

        Стратегия навигации меняется на каждом шаге:
        ReadableMixin → ReadableMixin → dict → dict → значение.
        """
        # Arrange — глубокая структура со смешанными типами
        user = UserInfo(
            user_id="42",
            extra={"settings": {"theme": "dark", "notifications": {"email": True}}},
        )
        ctx = Context(user=user)

        # Act & Assert — resolve переключает стратегию на каждом шаге
        assert ctx.resolve("user.extra.settings.theme") == "dark"
        assert ctx.resolve("user.extra.settings.notifications.email") is True

    def test_default_on_missing_intermediate(self) -> None:
        """
        Если промежуточный ключ не найден — resolve возвращает default,
        не бросая исключение. _resolve_one_step возвращает _SENTINEL,
        цикл прерывается, возвращается default.
        """
        # Arrange — структура без ключа "nonexistent"
        user = UserInfo(user_id="42", extra={"org": "acme"})
        ctx = Context(user=user)

        # Act — промежуточный ключ "nonexistent" не существует в UserInfo
        result = ctx.resolve("user.nonexistent.deep", default="N/A")

        # Assert — default, потому что цепочка прервалась на "nonexistent"
        assert result == "N/A"

    def test_default_on_missing_dict_key(self) -> None:
        """
        Промежуточный ключ не найден в словаре → default.
        """
        # Arrange — словарь с ключом "existing", но без "missing"
        user = UserInfo(extra={"existing": "value"})

        # Act — ключ "missing" не существует в extra
        result = user.resolve("extra.missing.deep", default="not found")

        # Assert — default, потому что _resolve_step_dict вернул _SENTINEL
        assert result == "not found"
