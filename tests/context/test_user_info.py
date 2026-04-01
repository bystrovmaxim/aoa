# tests/context/test_user_info.py
"""
Тесты UserInfo — информация о пользователе в контексте выполнения.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

UserInfo — dataclass с ReadableMixin, хранящий идентификатор пользователя,
список ролей и произвольные дополнительные данные (extra). Является частью
Context и используется машиной для проверки ролей через
ActionProductMachine._check_action_roles().

UserInfo создаётся:
- AuthCoordinator.process() — при аутентификации реального запроса.
- NoAuthCoordinator.process() — анонимный пользователь (user_id=None, roles=[]).
- Напрямую в тестах — через конструктор UserInfo(...).

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

Создание:
    - С полным набором полей (user_id, roles, extra).
    - С минимальными данными (только user_id).
    - Без аргументов — все поля по умолчанию (user_id=None, roles=[], extra={}).
    - С None в user_id — анонимный пользователь.

ReadableMixin — dict-подобный доступ:
    - __getitem__, __contains__, get, keys, values, items.
    - KeyError для несуществующих атрибутов.

ReadableMixin — resolve:
    - Плоские поля: resolve("user_id"), resolve("roles").
    - Вложенные через extra: resolve("extra.org").
    - Отсутствующие пути: resolve("missing") → None.

Поле extra:
    - Произвольные данные доступны через resolve("extra.key").
    - Вложенные словари: resolve("extra.nested.key").
    - Пустой extra: resolve("extra.missing") → default.
"""

import pytest

from action_machine.context.user_info import UserInfo

# ═════════════════════════════════════════════════════════════════════════════
# Создание и инициализация
# ═════════════════════════════════════════════════════════════════════════════


class TestUserInfoCreation:
    """Создание UserInfo с разными наборами параметров."""

    def test_create_with_all_fields(self) -> None:
        """
        UserInfo со всеми полями — типичный аутентифицированный пользователь.

        AuthCoordinator.process() создаёт UserInfo с данными из токена
        или API-ключа: user_id, roles и дополнительные данные в extra.
        """
        # Arrange & Act — создание с полным набором полей
        user = UserInfo(
            user_id="agent_007",
            roles=["admin", "manager"],
            extra={"org": "acme", "department": "sales"},
        )

        # Assert — все поля установлены
        assert user.user_id == "agent_007"
        assert user.roles == ["admin", "manager"]
        assert user.extra == {"org": "acme", "department": "sales"}

    def test_create_with_user_id_only(self) -> None:
        """
        UserInfo только с user_id — минимальный аутентифицированный пользователь.

        roles и extra получают значения по умолчанию из dataclass:
        roles=[], extra={}.
        """
        # Arrange & Act — только user_id
        user = UserInfo(user_id="u42")

        # Assert — user_id установлен, остальное по умолчанию
        assert user.user_id == "u42"
        assert user.roles == []
        assert user.extra == {}

    def test_create_default(self) -> None:
        """
        UserInfo без аргументов — анонимный пользователь.

        NoAuthCoordinator создаёт Context с UserInfo() — все поля
        по умолчанию: user_id=None, roles=[], extra={}.
        """
        # Arrange & Act — создание без аргументов
        user = UserInfo()

        # Assert — все поля по умолчанию
        assert user.user_id is None
        assert user.roles == []
        assert user.extra == {}

    def test_create_with_none_user_id(self) -> None:
        """
        user_id=None — явно анонимный пользователь.

        Эквивалентно UserInfo() по умолчанию, но может быть задано явно
        при создании контекста для гостевого доступа.
        """
        # Arrange & Act — явный None
        user = UserInfo(user_id=None, roles=["guest"])

        # Assert — user_id=None, но роль задана
        assert user.user_id is None
        assert user.roles == ["guest"]

    def test_roles_is_independent_list(self) -> None:
        """
        Каждый экземпляр UserInfo имеет свой список ролей.

        Dataclass field(default_factory=list) гарантирует, что
        roles — новый список для каждого экземпляра.
        """
        # Arrange — два экземпляра без явных ролей
        user1 = UserInfo(user_id="u1")
        user2 = UserInfo(user_id="u2")

        # Act — модификация ролей одного экземпляра
        user1.roles.append("admin")

        # Assert — второй экземпляр не затронут
        assert user1.roles == ["admin"]
        assert user2.roles == []


# ═════════════════════════════════════════════════════════════════════════════
# ReadableMixin — dict-подобный доступ
# ═════════════════════════════════════════════════════════════════════════════


class TestUserInfoDictAccess:
    """Dict-подобный доступ к полям UserInfo через ReadableMixin."""

    def test_getitem(self) -> None:
        """
        user["user_id"] — доступ к полю через квадратные скобки.

        ReadableMixin.__getitem__ делегирует в getattr(self, key).
        """
        # Arrange — UserInfo с user_id
        user = UserInfo(user_id="agent_007")

        # Act & Assert — чтение через скобки
        assert user["user_id"] == "agent_007"

    def test_getitem_missing_raises_key_error(self) -> None:
        """
        user["nonexistent"] → KeyError.

        ReadableMixin.__getitem__ ловит AttributeError и перебрасывает
        как KeyError — поведение идентично dict.
        """
        # Arrange — UserInfo без атрибута "nonexistent"
        user = UserInfo(user_id="u1")

        # Act & Assert — KeyError для несуществующего ключа
        with pytest.raises(KeyError):
            _ = user["nonexistent"]

    def test_contains(self) -> None:
        """
        "user_id" in user → True; "missing" in user → False.

        ReadableMixin.__contains__ делегирует в hasattr(self, key).
        """
        # Arrange
        user = UserInfo(user_id="u1", roles=["admin"])

        # Act & Assert — проверка наличия
        assert "user_id" in user
        assert "roles" in user
        assert "extra" in user
        assert "nonexistent" not in user

    def test_get_existing(self) -> None:
        """
        user.get("user_id") → значение атрибута.
        """
        # Arrange
        user = UserInfo(user_id="u1")

        # Act & Assert
        assert user.get("user_id") == "u1"

    def test_get_missing_with_default(self) -> None:
        """
        user.get("missing", "fallback") → "fallback".
        """
        # Arrange
        user = UserInfo(user_id="u1")

        # Act & Assert — отсутствующий ключ с default
        assert user.get("nonexistent", "fallback") == "fallback"

    def test_get_missing_without_default(self) -> None:
        """
        user.get("missing") → None (default по умолчанию).
        """
        # Arrange
        user = UserInfo(user_id="u1")

        # Act & Assert
        assert user.get("nonexistent") is None

    def test_keys(self) -> None:
        """
        keys() возвращает публичные поля dataclass.

        UserInfo — не pydantic, поэтому ReadableMixin использует
        vars(self) с фильтрацией приватных атрибутов.
        """
        # Arrange
        user = UserInfo(user_id="u1", roles=["admin"], extra={"org": "acme"})

        # Act
        keys = user.keys()

        # Assert — три публичных поля dataclass
        assert "user_id" in keys
        assert "roles" in keys
        assert "extra" in keys

    def test_values(self) -> None:
        """
        values() возвращает значения публичных полей.
        """
        # Arrange
        user = UserInfo(user_id="u1", roles=["admin"])

        # Act
        values = user.values()

        # Assert — значения присутствуют
        assert "u1" in values
        assert ["admin"] in values

    def test_items(self) -> None:
        """
        items() возвращает пары (ключ, значение) для публичных полей.
        """
        # Arrange
        user = UserInfo(user_id="u1")

        # Act
        items = user.items()

        # Assert — пара (user_id, "u1") присутствует
        assert ("user_id", "u1") in items


# ═════════════════════════════════════════════════════════════════════════════
# ReadableMixin — resolve
# ═════════════════════════════════════════════════════════════════════════════


class TestUserInfoResolve:
    """Навигация по полям UserInfo через resolve()."""

    def test_resolve_flat_field(self) -> None:
        """
        resolve("user_id") — прямой доступ к плоскому полю.

        Один сегмент пути, один вызов _resolve_one_step.
        """
        # Arrange
        user = UserInfo(user_id="agent_007")

        # Act
        result = user.resolve("user_id")

        # Assert
        assert result == "agent_007"

    def test_resolve_roles(self) -> None:
        """
        resolve("roles") — доступ к полю-списку.
        """
        # Arrange
        user = UserInfo(roles=["admin", "user"])

        # Act
        result = user.resolve("roles")

        # Assert — список целиком
        assert result == ["admin", "user"]

    def test_resolve_extra_value(self) -> None:
        """
        resolve("extra.org") — навигация через extra-словарь.

        Два шага: UserInfo → extra (dict) → значение.
        _resolve_one_step переключается с ReadableMixin на dict-стратегию.
        """
        # Arrange
        user = UserInfo(extra={"org": "acme"})

        # Act
        result = user.resolve("extra.org")

        # Assert
        assert result == "acme"

    def test_resolve_nested_extra(self) -> None:
        """
        resolve("extra.settings.theme") — глубокая навигация через extra.

        Три шага: UserInfo → extra (dict) → settings (dict) → theme (str).
        """
        # Arrange — вложенные словари в extra
        user = UserInfo(extra={"settings": {"theme": "dark", "lang": "ru"}})

        # Act
        result = user.resolve("extra.settings.theme")

        # Assert
        assert result == "dark"

    def test_resolve_missing_returns_none(self) -> None:
        """
        resolve("nonexistent") — отсутствующее поле → None.

        resolve никогда не бросает исключение при отсутствии ключа.
        """
        # Arrange
        user = UserInfo(user_id="u1")

        # Act
        result = user.resolve("nonexistent")

        # Assert — None как default по умолчанию
        assert result is None

    def test_resolve_missing_with_default(self) -> None:
        """
        resolve("nonexistent", default="N/A") → "N/A".
        """
        # Arrange
        user = UserInfo(user_id="u1")

        # Act
        result = user.resolve("nonexistent", default="N/A")

        # Assert
        assert result == "N/A"

    def test_resolve_none_user_id(self) -> None:
        """
        resolve("user_id") когда user_id=None → возвращает None, не default.

        None — валидное значение поля, не отсутствие. resolve различает
        "атрибут существует со значением None" и "атрибут не найден".
        """
        # Arrange — user_id явно None
        user = UserInfo(user_id=None)

        # Act
        result = user.resolve("user_id", default="fallback")

        # Assert — None из атрибута, не "fallback"
        assert result is None
