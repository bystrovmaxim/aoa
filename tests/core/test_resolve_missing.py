# tests/core/test_resolve_missing.py
"""
Тесты BaseSchema.resolve() для отсутствующих ключей и путей.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

resolve() никогда не бросает исключений при отсутствии ключа. Вместо
этого возвращает default (по умолчанию None). Это ключевое свойство:
шаблоны логирования ({%state.missing_field}) не должны ронять конвейер.

Механизм работы: на каждом шаге resolve проверяет тип текущего объекта:
- BaseSchema → __getitem__, KeyError → return default.
- dict → проверка ключа, отсутствие → return default.
- любой объект → getattr, None → return default.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

Отсутствие плоского поля:
    - resolve("missing") → None (default по умолчанию).
    - resolve("missing", default="X") → "X".
    - Не бросает KeyError или AttributeError.

Отсутствие вложенного поля:
    - resolve("user.nonexistent.deep") → default.
    - resolve("settings.missing.nested") → default (через наследника).

Отсутствие промежуточного ключа:
    - resolve("user.missing.key.deep") → default.
    - resolve("settings.existing.missing.deep") → default.
    - resolve("missing.segment.deep") → default (первый сегмент).

Разные типы default:
    - Строка, число, список, словарь, bool, None.

None как значение vs отсутствие:
    - Поле существует и равно None → resolve возвращает None, не default.
    - Поле отсутствует → resolve возвращает default.
    - Ключ в dict существует и равен None → None, не default.
    - Ключ в dict отсутствует → default.
"""

from typing import Any

from pydantic import ConfigDict

from action_machine.intents.context.context import Context
from action_machine.intents.context.request_info import RequestInfo
from action_machine.intents.context.runtime_info import RuntimeInfo
from action_machine.intents.context.user_info import UserInfo
from tests.domain_model.roles import AdminRole, UserRole

# ═════════════════════════════════════════════════════════════════════════════
# Наследники Info-классов для тестов вложенной навигации
# ═════════════════════════════════════════════════════════════════════════════


class _ExtendedUserInfo(UserInfo):
    """Наследник UserInfo с дополнительными полями для тестов."""
    model_config = ConfigDict(frozen=True)
    org: str | None = None
    settings: dict[str, Any] = {}


# ═════════════════════════════════════════════════════════════════════════════
# Вспомогательная функция
# ═════════════════════════════════════════════════════════════════════════════


def _make_full_context(user_id: str = "agent_1") -> Context:
    """
    Создаёт Context со всеми компонентами для тестов вложенных путей.

    Использует _ExtendedUserInfo с полем org для тестирования
    трёхуровневой навигации.
    """
    user = _ExtendedUserInfo(
        user_id=user_id,
        roles=(UserRole, AdminRole),
        org="acme",
    )
    request = RequestInfo(
        trace_id="trace-abc-123",
        request_path="/api/v1/orders",
        request_method="POST",
    )
    runtime = RuntimeInfo(
        hostname="pod-xyz-42",
        service_name="order-service",
    )
    return Context(user=user, request=request, runtime=runtime)


# ═════════════════════════════════════════════════════════════════════════════
# Отсутствие плоского поля
# ═════════════════════════════════════════════════════════════════════════════


class TestMissingFlat:
    """Отсутствие плоского поля — resolve возвращает default."""

    def test_missing_returns_none_by_default(self) -> None:
        """
        resolve("nonexistent") без default — возвращает None.
        """
        # Arrange — UserInfo без поля "nonexistent"
        user = UserInfo(user_id="42")

        # Act
        result = user.resolve("nonexistent")

        # Assert
        assert result is None

    def test_missing_returns_explicit_default(self) -> None:
        """
        resolve("missing", default="<none>") — возвращает указанный default.
        """
        # Arrange
        user = UserInfo(user_id="42")

        # Act
        result = user.resolve("missing", default="<none>")

        # Assert
        assert result == "<none>"

    def test_missing_does_not_raise(self) -> None:
        """
        resolve() никогда не бросает KeyError или AttributeError.
        Критически важно для шаблонов логирования.
        """
        # Arrange
        user = UserInfo(user_id="42")

        # Act — resolve по несуществующему пути, включая вложенный
        result_flat = user.resolve("missing")
        result_nested = user.resolve("missing.key")

        # Assert — оба вызова вернули None без исключений
        assert result_flat is None
        assert result_nested is None


# ═════════════════════════════════════════════════════════════════════════════
# Отсутствие вложенного поля
# ═════════════════════════════════════════════════════════════════════════════


class TestMissingNested:
    """Отсутствие поля на вложенном уровне — resolve возвращает default."""

    def test_missing_in_schema(self) -> None:
        """
        resolve("user.nonexistent.deep") — промежуточный атрибут
        "nonexistent" не существует в UserInfo.

        Первый шаг: Context → UserInfo (OK).
        Второй шаг: UserInfo → "nonexistent" → KeyError → default.
        """
        # Arrange
        ctx = _make_full_context()

        # Act
        result = ctx.resolve("user.nonexistent.deep", default="N/A")

        # Assert
        assert result == "N/A"

    def test_missing_in_dict(self) -> None:
        """
        resolve("user.settings.missing.deep") — промежуточный ключ "missing"
        не существует в словаре settings.

        Первый шаг: Context → _ExtendedUserInfo (OK).
        Второй шаг: _ExtendedUserInfo → settings (dict, OK).
        Третий шаг: dict → "missing" → не найден → default.
        """
        # Arrange — наследник UserInfo с dict-полем settings
        user = _ExtendedUserInfo(settings={"existing": "value"})

        # Act
        result = user.resolve("settings.missing.deep", default="not found")

        # Assert
        assert result == "not found"

    def test_missing_with_default_none(self) -> None:
        """
        resolve("user.nonexistent.deep", default=None) — явный None как default.
        """
        # Arrange
        ctx = _make_full_context()

        # Act
        result = ctx.resolve("user.nonexistent.deep", default=None)

        # Assert
        assert result is None


# ═════════════════════════════════════════════════════════════════════════════
# Отсутствие промежуточного ключа в цепочке
# ═════════════════════════════════════════════════════════════════════════════


class TestMissingIntermediate:
    """Отсутствие промежуточного ключа в длинной цепочке."""

    def test_missing_intermediate_in_schema(self) -> None:
        """
        resolve("user.missing.key.deep") — "missing" не существует
        в UserInfo. Цепочка прерывается на втором сегменте.
        """
        # Arrange
        ctx = _make_full_context()

        # Act
        result = ctx.resolve("user.missing.key.deep", default="fallback")

        # Assert
        assert result == "fallback"

    def test_missing_intermediate_in_dict(self) -> None:
        """
        resolve("settings.existing.missing.deep") — "existing" найден,
        но "missing" в его значении отсутствует.
        """
        # Arrange
        user = _ExtendedUserInfo(settings={"existing": {"key": "value"}})

        # Act
        result = user.resolve("settings.existing.missing.deep", default="none")

        # Assert
        assert result == "none"

    def test_missing_first_segment(self) -> None:
        """
        resolve("missing.segment.deep") — первый же сегмент не найден.
        """
        # Arrange
        user = UserInfo(user_id="42")

        # Act
        result = user.resolve("missing.segment.deep", default="first missing")

        # Assert
        assert result == "first missing"


# ═════════════════════════════════════════════════════════════════════════════
# Разные типы default
# ═════════════════════════════════════════════════════════════════════════════


class TestDefaultTypes:
    """resolve возвращает default любого типа при отсутствии пути."""

    def test_default_string(self) -> None:
        """default — строка."""
        user = UserInfo(user_id="42")
        result = user.resolve("missing", default="default string")
        assert result == "default string"

    def test_default_int(self) -> None:
        """default — целое число."""
        user = UserInfo(user_id="42")
        result = user.resolve("missing", default=42)
        assert result == 42

    def test_default_list(self) -> None:
        """default — список."""
        user = UserInfo(user_id="42")
        result = user.resolve("missing", default=[1, 2, 3])
        assert result == [1, 2, 3]

    def test_default_dict(self) -> None:
        """default — словарь."""
        user = UserInfo(user_id="42")
        result = user.resolve("missing", default={"key": "value"})
        assert result == {"key": "value"}

    def test_default_bool_true(self) -> None:
        """default — True."""
        user = UserInfo(user_id="42")
        result = user.resolve("missing_true", default=True)
        assert result is True

    def test_default_bool_false(self) -> None:
        """default — False."""
        user = UserInfo(user_id="42")
        result = user.resolve("missing_false", default=False)
        assert result is False


# ═════════════════════════════════════════════════════════════════════════════
# None как значение vs отсутствие поля
# ═════════════════════════════════════════════════════════════════════════════


class TestNoneVsMissing:
    """
    Различие между "поле существует со значением None" и "поле отсутствует".
    """

    def test_existing_none_field_returns_none(self) -> None:
        """
        Поле user_id=None — существует, значение None.
        resolve возвращает None, а не default.
        """
        # Arrange
        user = UserInfo(user_id=None)

        # Act
        result = user.resolve("user_id", default="fallback")

        # Assert — None из поля, не "fallback"
        assert result is None

    def test_missing_field_returns_default(self) -> None:
        """
        Поле "nonexistent" не существует → resolve возвращает default.
        """
        # Arrange
        user = UserInfo(user_id="42")

        # Act
        result = user.resolve("nonexistent", default="fallback")

        # Assert
        assert result == "fallback"

    def test_none_in_dict_returns_none(self) -> None:
        """
        Ключ в dict существует со значением None — resolve возвращает None.
        """
        # Arrange — наследник с dict-полем содержащим None
        user = _ExtendedUserInfo(settings={"key_with_none": None})

        # Act
        result = user.resolve("settings.key_with_none", default="fallback")

        # Assert — None из словаря, не "fallback"
        assert result is None

    def test_missing_key_in_dict_returns_default(self) -> None:
        """
        Ключ в dict не существует — resolve возвращает default.
        """
        # Arrange
        user = _ExtendedUserInfo(settings={"existing": "value"})

        # Act
        result = user.resolve("settings.missing_key", default="fallback")

        # Assert
        assert result == "fallback"
