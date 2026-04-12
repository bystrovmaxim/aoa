# tests/context/test_user_info.py
"""
Тесты UserInfo — информация о пользователе в контексте выполнения.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

UserInfo — frozen pydantic-модель (наследник BaseSchema), хранящая
идентификатор пользователя и список ролей. Является частью Context
и используется машиной для проверки ролей через
ActionProductMachine._check_action_roles().

UserInfo создаётся:
- AuthCoordinator.process() — при аутентификации реального запроса.
- NoAuthCoordinator.process() — анонимный пользователь (user_id=None, roles=()).
- Напрямую в тестах — через конструктор UserInfo(...).

Произвольные поля запрещены (extra="forbid"). Расширение — только через
наследование с явно объявленными полями.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

Создание:
    - С полным набором полей (user_id, roles).
    - С минимальными данными (только user_id).
    - Без аргументов — user_id=None, roles=().
    - С None в user_id — анонимный пользователь.

BaseSchema — dict-подобный доступ:
    - __getitem__, __contains__, get, keys, values, items.
    - KeyError для несуществующих полей.

BaseSchema — resolve:
    - Плоские поля: resolve("user_id"), resolve("roles").
    - Отсутствующие пути: resolve("missing") → None.

Расширение через наследование:
    - Наследник с дополнительными полями (org, settings).
    - resolve через наследника: resolve("org"), resolve("settings.theme").
"""

from typing import Any

import pytest
from pydantic import ConfigDict

from action_machine.context.user_info import UserInfo
from tests.domain_model.roles import AdminRole, GuestRole, ManagerRole, UserRole

# ═════════════════════════════════════════════════════════════════════════════
# Наследник UserInfo для тестов расширения
# ═════════════════════════════════════════════════════════════════════════════


class _ExtendedUserInfo(UserInfo):
    """Наследник UserInfo с дополнительными полями для тестов."""
    model_config = ConfigDict(frozen=True)
    org: str | None = None
    department: str | None = None
    settings: dict[str, Any] = {}


# ═════════════════════════════════════════════════════════════════════════════
# Создание и инициализация
# ═════════════════════════════════════════════════════════════════════════════


class TestUserInfoCreation:
    """Создание UserInfo с разными наборами параметров."""

    def test_create_with_all_fields(self) -> None:
        """
        UserInfo со всеми полями — типичный аутентифицированный пользователь.

        AuthCoordinator.process() создаёт UserInfo с данными из токена
        или API-ключа: user_id и roles.
        """
        # Arrange & Act — создание с полным набором полей
        user = UserInfo(
            user_id="agent_007",
            roles=(AdminRole, ManagerRole),
        )

        # Assert — все поля установлены
        assert user.user_id == "agent_007"
        assert user.roles == (AdminRole, ManagerRole)

    def test_create_with_user_id_only(self) -> None:
        """
        UserInfo только с user_id — минимальный аутентифицированный пользователь.
        roles получает значение по умолчанию: ().
        """
        # Arrange & Act — только user_id
        user = UserInfo(user_id="u42")

        # Assert — user_id установлен, roles по умолчанию
        assert user.user_id == "u42"
        assert user.roles == ()

    def test_create_default(self) -> None:
        """
        UserInfo без аргументов — анонимный пользователь.
        NoAuthCoordinator создаёт Context с UserInfo() — все поля
        по умолчанию: user_id=None, roles=().
        """
        # Arrange & Act — создание без аргументов
        user = UserInfo()

        # Assert — все поля по умолчанию
        assert user.user_id is None
        assert user.roles == ()

    def test_create_with_none_user_id(self) -> None:
        """
        user_id=None — явно анонимный пользователь.
        Эквивалентно UserInfo() по умолчанию, но может быть задано явно
        при создании контекста для гостевого доступа.
        """
        # Arrange & Act — явный None
        user = UserInfo(user_id=None, roles=(GuestRole,))

        # Assert — user_id=None, но роль задана
        assert user.user_id is None
        assert user.roles == (GuestRole,)

    def test_extended_user_info_with_extra_fields(self) -> None:
        """
        Расширение UserInfo через наследование с явно объявленными полями.

        UserInfo имеет extra="forbid" — произвольные поля запрещены.
        Для дополнительных данных создаётся наследник.
        """
        # Arrange & Act — наследник с дополнительными полями
        user = _ExtendedUserInfo(
            user_id="agent_007",
            roles=(AdminRole, ManagerRole),
            org="acme",
            department="sales",
        )

        # Assert — все поля установлены
        assert user.user_id == "agent_007"
        assert user.roles == (AdminRole, ManagerRole)
        assert user.org == "acme"
        assert user.department == "sales"


# ═════════════════════════════════════════════════════════════════════════════
# BaseSchema — dict-подобный доступ
# ═════════════════════════════════════════════════════════════════════════════


class TestUserInfoDictAccess:
    """Dict-подобный доступ к полям UserInfo через BaseSchema."""

    def test_getitem(self) -> None:
        """
        user["user_id"] — доступ к полю через квадратные скобки.
        BaseSchema.__getitem__ делегирует в getattr(self, key).
        """
        # Arrange — UserInfo с user_id
        user = UserInfo(user_id="agent_007")

        # Act & Assert — чтение через скобки
        assert user["user_id"] == "agent_007"

    def test_getitem_missing_raises_key_error(self) -> None:
        """
        user["nonexistent"] → KeyError.
        BaseSchema.__getitem__ ловит AttributeError и перебрасывает
        как KeyError — поведение идентично dict.
        """
        # Arrange — UserInfo без поля "nonexistent"
        user = UserInfo(user_id="u1")

        # Act & Assert — KeyError для несуществующего ключа
        with pytest.raises(KeyError):
            _ = user["nonexistent"]

    def test_contains(self) -> None:
        """
        "user_id" in user → True; "missing" in user → False.
        BaseSchema.__contains__ проверяет model_fields.
        """
        # Arrange
        user = UserInfo(user_id="u1", roles=(AdminRole,))

        # Act & Assert — проверка наличия объявленных полей
        assert "user_id" in user
        assert "roles" in user
        assert "nonexistent" not in user

    def test_get_existing(self) -> None:
        """
        user.get("user_id") → значение поля.
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
        keys() возвращает объявленные pydantic-поля.
        UserInfo имеет два поля: user_id, roles.
        """
        # Arrange
        user = UserInfo(user_id="u1", roles=(AdminRole,))

        # Act
        keys = user.keys()

        # Assert — два объявленных поля
        assert "user_id" in keys
        assert "roles" in keys

    def test_values(self) -> None:
        """
        values() возвращает значения объявленных полей.
        """
        # Arrange
        user = UserInfo(user_id="u1", roles=(AdminRole,))

        # Act
        values = user.values()

        # Assert — значения присутствуют
        assert "u1" in values
        assert (AdminRole,) in values

    def test_items(self) -> None:
        """
        items() возвращает пары (ключ, значение) для объявленных полей.
        """
        # Arrange
        user = UserInfo(user_id="u1")

        # Act
        items = user.items()

        # Assert — пара (user_id, "u1") присутствует
        assert ("user_id", "u1") in items


# ═════════════════════════════════════════════════════════════════════════════
# BaseSchema — resolve
# ═════════════════════════════════════════════════════════════════════════════


class TestUserInfoResolve:
    """Навигация по полям UserInfo через resolve()."""

    def test_resolve_flat_field(self) -> None:
        """
        resolve("user_id") — прямой доступ к плоскому полю.
        """
        # Arrange
        user = UserInfo(user_id="agent_007")

        # Act
        result = user.resolve("user_id")

        # Assert
        assert result == "agent_007"

    def test_resolve_roles(self) -> None:
        """
        resolve("roles") — доступ к кортежу типов ролей.
        """
        # Arrange
        user = UserInfo(roles=(AdminRole, UserRole))

        # Act
        result = user.resolve("roles")

        # Assert — кортеж целиком
        assert result == (AdminRole, UserRole)

    def test_resolve_extended_field(self) -> None:
        """
        resolve("org") на наследнике — навигация к полю наследника.
        """
        # Arrange — наследник с полем org
        user = _ExtendedUserInfo(org="acme")

        # Act
        result = user.resolve("org")

        # Assert
        assert result == "acme"

    def test_resolve_extended_nested_dict(self) -> None:
        """
        resolve("settings.theme") на наследнике — навигация через dict-поле.

        Два шага: _ExtendedUserInfo → settings (dict) → theme (str).
        resolve переключается с BaseSchema.__getitem__ на dict-доступ.
        """
        # Arrange — наследник с dict-полем settings
        user = _ExtendedUserInfo(settings={"theme": "dark", "lang": "ru"})

        # Act
        result = user.resolve("settings.theme")

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
        None — валидное значение поля, не отсутствие.
        """
        # Arrange — user_id явно None
        user = UserInfo(user_id=None)

        # Act
        result = user.resolve("user_id", default="fallback")

        # Assert — None из поля, не "fallback"
        assert result is None
