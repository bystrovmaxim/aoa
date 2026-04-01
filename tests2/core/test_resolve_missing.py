# tests2/core/test_resolve_missing.py
"""
Тесты ReadableMixin.resolve() для отсутствующих ключей и путей.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

resolve() никогда не бросает исключений при отсутствии ключа. Вместо
этого возвращает default (по умолчанию None). Это ключевое свойство:
шаблоны логирования ({%state.missing_field}) не должны ронять конвейер.

Механизм работы: на каждом шаге _resolve_one_step возвращает _SENTINEL
если атрибут/ключ не найден. Цикл в resolve() проверяет результат:
если _SENTINEL — записывает default в кеш и возвращает его.

Этот файл покрывает все сценарии отсутствия:
- Плоское поле не существует.
- Промежуточный ключ в цепочке не найден (в ReadableMixin или dict).
- Первый сегмент пути отсутствует.
- Разные типы default (строка, число, список, dict, bool, None).
- Различие между "поле существует со значением None" и "поле отсутствует".

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

Отсутствие плоского поля:
    - resolve("missing") → None (default по умолчанию).
    - resolve("missing", default="X") → "X".
    - Не бросает KeyError или AttributeError.

Отсутствие вложенного поля:
    - resolve("user.nonexistent.deep") → default.
    - resolve("extra.missing.nested") → default.

Отсутствие промежуточного ключа:
    - resolve("user.missing.key.deep") → default.
    - resolve("extra.existing.missing.deep") → default.
    - resolve("missing.segment.deep") → default (первый сегмент).

Разные типы default:
    - Строка, число, список, словарь, bool, None.

None как значение vs отсутствие:
    - Поле существует и равно None → resolve возвращает None, не default.
    - Поле отсутствует → resolve возвращает default.
    - Ключ в dict существует и равен None → None, не default.
    - Ключ в dict отсутствует → default.
"""

from action_machine.context.context import Context
from action_machine.context.request_info import RequestInfo
from action_machine.context.runtime_info import RuntimeInfo
from action_machine.context.user_info import UserInfo

# ═════════════════════════════════════════════════════════════════════════════
# Вспомогательная функция
# ═════════════════════════════════════════════════════════════════════════════


def _make_full_context(user_id: str = "agent_1") -> Context:
    """
    Создаёт Context со всеми компонентами для тестов вложенных путей.

    Включает UserInfo с extra-словарём, RequestInfo с trace_id
    и RuntimeInfo с hostname. Используется для тестирования
    отсутствия ключей на разных уровнях вложенности.
    """
    user = UserInfo(
        user_id=user_id,
        roles=["user", "admin"],
        extra={"org": "acme"},
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

        _resolve_one_step(UserInfo, "nonexistent") → getattr не находит
        атрибут → возвращает _SENTINEL. Цикл в resolve прерывается,
        default=None записывается в кеш и возвращается.
        """
        # Arrange — UserInfo без атрибута "nonexistent"
        user = UserInfo(user_id="42")

        # Act — resolve без явного default
        result = user.resolve("nonexistent")

        # Assert — None как default по умолчанию
        assert result is None

    def test_missing_returns_explicit_default(self) -> None:
        """
        resolve("missing", default="<none>") — возвращает указанный default.
        """
        # Arrange — UserInfo без атрибута "missing"
        user = UserInfo(user_id="42")

        # Act — resolve с явным default
        result = user.resolve("missing", default="<none>")

        # Assert — возвращён переданный default
        assert result == "<none>"

    def test_missing_does_not_raise(self) -> None:
        """
        resolve() никогда не бросает KeyError или AttributeError.

        Это критически важно для шаблонов логирования: {%state.missing}
        не должен ронять конвейер выполнения действия.
        """
        # Arrange — UserInfo с минимальными данными
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

    def test_missing_in_readable(self) -> None:
        """
        resolve("user.nonexistent.deep") — промежуточный атрибут
        "nonexistent" не существует в UserInfo.

        Первый шаг: Context → UserInfo (OK).
        Второй шаг: UserInfo → "nonexistent" → _SENTINEL (нет атрибута).
        Цикл прерывается → default.
        """
        # Arrange — Context с UserInfo, у которого нет "nonexistent"
        ctx = _make_full_context()

        # Act — промежуточный атрибут отсутствует
        result = ctx.resolve("user.nonexistent.deep", default="N/A")

        # Assert — default, цепочка прервалась на втором шаге
        assert result == "N/A"

    def test_missing_in_dict(self) -> None:
        """
        resolve("extra.missing.deep") — промежуточный ключ "missing"
        не существует в словаре extra.

        Первый шаг: UserInfo → extra (dict, OK).
        Второй шаг: dict → "missing" → _SENTINEL (нет ключа).
        Цикл прерывается → default.
        """
        # Arrange — UserInfo с extra-словарём без ключа "missing"
        user = UserInfo(extra={"existing": "value"})

        # Act — ключ "missing" не найден в dict
        result = user.resolve("extra.missing.deep", default="not found")

        # Assert — default
        assert result == "not found"

    def test_missing_with_default_none(self) -> None:
        """
        resolve("user.nonexistent.deep", default=None) — явный None
        как default. Результат тот же, что и без default, но
        показывает осознанный выбор вызывающего кода.
        """
        # Arrange — Context без атрибута "nonexistent" на UserInfo
        ctx = _make_full_context()

        # Act — default=None явно
        result = ctx.resolve("user.nonexistent.deep", default=None)

        # Assert — None
        assert result is None


# ═══════════════════════════════════════════════════════════════════════════

# Отсутствие промежуточного ключа в цепочке
# ═════════════════════════════════════════════════════════════════════════════


class TestMissingIntermediate:
    """Отсутствие промежуточного ключа в длинной цепочке."""

    def test_missing_intermediate_in_readable(self) -> None:
        """
        resolve("user.missing.key.deep") — "missing" не существует
        в UserInfo, хотя "user" существует в Context.

        Цепочка прерывается на втором сегменте "missing".
        Оставшиеся сегменты "key" и "deep" не обрабатываются.
        """
        # Arrange — Context с UserInfo без атрибута "missing"
        ctx = _make_full_context()

        # Act — длинный путь, прерывающийся на втором сегменте
        result = ctx.resolve("user.missing.key.deep", default="fallback")

        # Assert — default, потому что цепочка прервалась рано
        assert result == "fallback"

    def test_missing_intermediate_in_dict(self) -> None:
        """
        resolve("extra.existing.missing.deep") — "existing" найден,
        но "missing" в его значении (словаре {"key": "value"}) отсутствует.
        """
        # Arrange — двухуровневый словарь, но без ключа "missing"
        user = UserInfo(extra={"existing": {"key": "value"}})

        # Act — "existing" → {"key": "value"}, "missing" не найден в этом dict
        result = user.resolve("extra.existing.missing.deep", default="none")

        # Assert — default
        assert result == "none"

    def test_missing_first_segment(self) -> None:
        """
        resolve("missing.segment.deep") — первый же сегмент "missing"
        не найден на объекте.

        _resolve_one_step(self, "missing") сразу возвращает _SENTINEL.
        """
        # Arrange — UserInfo без атрибута "missing"
        user = UserInfo(user_id="42")

        # Act — первый сегмент отсутствует
        result = user.resolve("missing.segment.deep", default="first missing")

        # Assert — default с первого же шага
        assert result == "first missing"


# ═════════════════════════════════════════════════════════════════════════════
# Разные типы default
# ═════════════════════════════════════════════════════════════════════════════


class TestDefaultTypes:
    """resolve возвращает default любого типа при отсутствии пути."""

    def test_default_string(self) -> None:
        """default — строка."""
        # Arrange — объект без атрибута "missing"
        user = UserInfo(user_id="42")

        # Act — resolve с default-строкой
        result = user.resolve("missing", default="default string")

        # Assert — строка-default
        assert result == "default string"

    def test_default_int(self) -> None:
        """default — целое число."""
        # Arrange
        user = UserInfo(user_id="42")

        # Act
        result = user.resolve("missing", default=42)

        # Assert
        assert result == 42

    def test_default_list(self) -> None:
        """default — список."""
        # Arrange
        user = UserInfo(user_id="42")

        # Act
        result = user.resolve("missing", default=[1, 2, 3])

        # Assert
        assert result == [1, 2, 3]

    def test_default_dict(self) -> None:
        """default — словарь."""
        # Arrange
        user = UserInfo(user_id="42")

        # Act
        result = user.resolve("missing", default={"key": "value"})

        # Assert
        assert result == {"key": "value"}

    def test_default_bool_true(self) -> None:
        """default — True."""
        # Arrange — новый экземпляр, чтобы кеш не влиял
        user = UserInfo(user_id="42")

        # Act
        result = user.resolve("missing_true", default=True)

        # Assert
        assert result is True

    def test_default_bool_false(self) -> None:
        """default — False. Falsy-значение, но это именно default."""
        # Arrange — новый экземпляр для чистого кеша
        user = UserInfo(user_id="42")

        # Act
        result = user.resolve("missing_false", default=False)

        # Assert
        assert result is False


# ═════════════════════════════════════════════════════════════════════════════
# None как значение vs отсутствие поля
# ═════════════════════════════════════════════════════════════════════════════


class TestNoneVsMissing:
    """
    Различие между "поле существует со значением None" и "поле отсутствует".

    Это критически важное поведение: resolve проверяет наличие атрибута
    через _SENTINEL, а не через truthiness значения. None — это валидное
    значение, которое не должно заменяться на default.
    """

    def test_existing_none_field_returns_none(self) -> None:
        """
        Поле user_id=None — существует, значение None.

        _resolve_one_step возвращает None (не _SENTINEL), поэтому
        resolve возвращает None, а не default.
        """
        # Arrange — user_id явно установлен в None
        user = UserInfo(user_id=None)

        # Act — resolve с default="fallback"
        result = user.resolve("user_id", default="fallback")

        # Assert — None из атрибута, не "fallback"
        assert result is None

    def test_missing_field_returns_default(self) -> None:
        """
        Поле "nonexistent" не существует на объекте.

        _resolve_one_step возвращает _SENTINEL, поэтому resolve
        возвращает default.
        """
        # Arrange — UserInfo без атрибута "nonexistent"
        user = UserInfo(user_id="42")

        # Act — resolve несуществующего атрибута
        result = user.resolve("nonexistent", default="fallback")

        # Assert — "fallback" из default
        assert result == "fallback"

    def test_none_in_dict_returns_none(self) -> None:
        """
        Ключ в dict существует со значением None — resolve возвращает None.

        _resolve_step_dict проверяет "segment in current", ключ найден,
        dict["key"] → None, _SENTINEL не возвращается.
        """
        # Arrange — ключ "key_with_none" со значением None в extra
        user = UserInfo(extra={"key_with_none": None})

        # Act — resolve с default="fallback"
        result = user.resolve("extra.key_with_none", default="fallback")

        # Assert — None из словаря, не "fallback"
        assert result is None

    def test_missing_key_in_dict_returns_default(self) -> None:
        """
        Ключ в dict не существует — resolve возвращает default.

        _resolve_step_dict: "missing_key" not in current → _SENTINEL.
        """
        # Arrange — extra без ключа "missing_key"
        user = UserInfo(extra={"existing": "value"})

        # Act — resolve несуществующего ключа в dict
        result = user.resolve("extra.missing_key", default="fallback")

        # Assert — "fallback" из default
        assert result == "fallback"
