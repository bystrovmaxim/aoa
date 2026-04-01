# tests2/core/test_resolve_flat.py
"""
Тесты ReadableMixin.resolve() для плоских полей (без вложенности).

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Метод resolve(dotpath, default) — основной механизм навигации по данным
в системе логирования ActionMachine. Шаблоны вида {%context.user.user_id},
{%state.total}, {%params.amount} разрешаются через resolve().

Этот файл тестирует самый простой случай: плоские поля без вложенности.
resolve("user_id") эквивалентно getattr(self, "user_id"), но с поддержкой
default и без выброса исключений при отсутствии атрибута.

Плоский resolve — это однократный вызов _resolve_one_step() с единственным
сегментом пути. Более сложные случаи (вложенные объекты, словари,
разные типы данных, кеширование) покрыты в отдельных файлах:
test_resolve_nested.py, test_resolve_missing.py, test_resolve_types.py,
test_resolve_caching.py.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

Базовый доступ:
    - Строковое поле — resolve возвращает строку.
    - Числовое поле — resolve возвращает int или float.
    - Поле-список — resolve возвращает list целиком.
    - Поле с default — для существующего ключа default игнорируется.

None как значение:
    - Поле со значением None — resolve возвращает None, не default.
    - None с default — default НЕ подставляется, потому что поле существует.

Разные типы объектов:
    - UserInfo (dataclass + ReadableMixin) — плоские поля.
    - BaseState (динамические поля + ReadableMixin) — плоские поля.
    - BaseParams (pydantic + ReadableMixin) — плоские поля.
"""

from pydantic import Field

from action_machine.context.user_info import UserInfo
from action_machine.core.base_params import BaseParams
from action_machine.core.base_state import BaseState

# ═════════════════════════════════════════════════════════════════════════════
# Базовый доступ к плоским полям
# ═════════════════════════════════════════════════════════════════════════════


class TestResolveFlatBasic:
    """Базовый доступ к плоским полям через resolve()."""

    def test_resolve_string_field(self) -> None:
        """
        resolve("user_id") возвращает строковое значение атрибута.

        UserInfo — dataclass с ReadableMixin. resolve разбивает
        "user_id" по точкам → ["user_id"], вызывает
        _resolve_one_step(self, "user_id") → getattr(self, "user_id").
        """
        # Arrange — UserInfo с user_id="agent_007"
        user = UserInfo(user_id="agent_007", roles=["agent"])

        # Act — resolve по одному сегменту, без вложенности
        result = user.resolve("user_id")

        # Assert — строковое значение из атрибута user.user_id
        assert result == "agent_007"

    def test_resolve_list_field(self) -> None:
        """
        resolve("roles") возвращает список целиком.

        resolve не поддерживает индексацию списков (roles.0).
        Для получения элемента нужно сначала получить список,
        потом обращаться к элементу в Python-коде.
        """
        # Arrange — UserInfo с двумя ролями
        user = UserInfo(user_id="42", roles=["admin", "user"])

        # Act — resolve возвращает весь список
        result = user.resolve("roles")

        # Assert — список из двух элементов, тип сохранён
        assert result == ["admin", "user"]
        assert isinstance(result, list)

    def test_resolve_existing_field_ignores_default(self) -> None:
        """
        Для существующего поля default игнорируется.

        resolve("user_id", default="N/A") возвращает реальное значение,
        а не default. Default используется только если путь не найден.
        """
        # Arrange — UserInfo с user_id="42"
        user = UserInfo(user_id="42")

        # Act — resolve с default, но поле существует
        result = user.resolve("user_id", default="N/A")

        # Assert — реальное значение "42", а не default "N/A"
        assert result == "42"


# ═════════════════════════════════════════════════════════════════════════════
# None как значение поля
# ═════════════════════════════════════════════════════════════════════════════


class TestResolveFlatNone:
    """None как значение поля — отличие от отсутствия поля."""

    def test_resolve_none_value(self) -> None:
        """
        Поле со значением None — resolve возвращает None.

        UserInfo(user_id=None) — поле user_id существует, но равно None.
        resolve НЕ считает None отсутствием: _resolve_one_step вернул
        не _SENTINEL, а реальное значение None.
        """
        # Arrange — user_id явно установлен в None
        user = UserInfo(user_id=None)

        # Act — resolve находит атрибут, его значение — None
        result = user.resolve("user_id")

        # Assert — возвращён None, а не default
        assert result is None

    def test_resolve_none_value_ignores_default(self) -> None:
        """
        None с default — default НЕ подставляется.

        Ключевое отличие от отсутствия поля: если поле существует
        и равно None, default не применяется. Default применяется
        только когда _resolve_one_step вернул _SENTINEL (атрибут
        не найден через getattr).
        """
        # Arrange — user_id явно равен None
        user = UserInfo(user_id=None)

        # Act — resolve с default="fallback"
        result = user.resolve("user_id", default="fallback")

        # Assert — возвращён None, а не "fallback",
        # потому что поле существует (хоть и равно None)
        assert result is None


# ═════════════════════════════════════════════════════════════════════════════
# Разные типы объектов с ReadableMixin
# ═════════════════════════════════════════════════════════════════════════════


class TestResolveFlatDifferentObjects:
    """resolve() работает единообразно на разных типах объектов."""

    def test_resolve_on_base_state(self) -> None:
        """
        resolve() на BaseState — динамические атрибуты.

        BaseState не является pydantic-моделью. ReadableMixin для него
        использует ветку vars(self) в _get_field_names(). resolve
        обращается к атрибутам через _resolve_step_readable → __getitem__
        → getattr.
        """
        # Arrange — BaseState с двумя динамическими полями
        state = BaseState({"txn_id": "TXN-001", "total": 1500.0})

        # Act — resolve плоских полей
        txn_id = state.resolve("txn_id")
        total = state.resolve("total")

        # Assert — значения из динамических атрибутов
        assert txn_id == "TXN-001"
        assert total == 1500.0

    def test_resolve_on_pydantic_params(self) -> None:
        """
        resolve() на pydantic BaseParams — объявленные поля модели.

        BaseParams наследует pydantic BaseModel. ReadableMixin определяет
        это через isinstance(self, BaseModel) и использует model_fields
        для списка полей. resolve обращается к значениям через getattr,
        который работает одинаково для pydantic и обычных классов.
        """
        # Arrange — pydantic-модель с описанными полями
        class TestParams(BaseParams):
            name: str = Field(description="Имя")
            count: int = Field(description="Количество")

        params = TestParams(name="test", count=5)

        # Act — resolve плоских полей pydantic-модели
        name = params.resolve("name")
        count = params.resolve("count")

        # Assert — значения из pydantic-полей
        assert name == "test"
        assert count == 5

    def test_resolve_on_user_info(self) -> None:
        """
        resolve() на UserInfo — dataclass с ReadableMixin.

        UserInfo — @dataclass с полями user_id, roles, extra.
        ReadableMixin работает через vars(self) для не-pydantic объектов.
        """
        # Arrange — UserInfo со всеми полями
        user = UserInfo(
            user_id="test_user",
            roles=["admin", "manager"],
            extra={"org": "acme"},
        )

        # Act — resolve каждого плоского поля
        user_id = user.resolve("user_id")
        roles = user.resolve("roles")
        extra = user.resolve("extra")

        # Assert — каждое поле возвращает своё значение с правильным типом
        assert user_id == "test_user"
        assert roles == ["admin", "manager"]
        assert extra == {"org": "acme"}

    def test_resolve_empty_string_field(self) -> None:
        """
        Пустая строка "" — это валидное значение, не отсутствие.

        resolve возвращает "", а не default.
        """
        # Arrange — user_id = пустая строка
        user = UserInfo(user_id="")

        # Act — resolve находит атрибут, его значение — ""
        result = user.resolve("user_id")

        # Assert — пустая строка, не None и не default
        assert result == ""
        assert isinstance(result, str)

    def test_resolve_zero_value(self) -> None:
        """
        Числовой ноль 0 — это валидное значение, не отсутствие.

        resolve возвращает 0, а не default. Ноль — falsy в Python,
        но resolve проверяет через _SENTINEL, а не через truthiness.
        """
        # Arrange — state с нулевым значением
        state = BaseState({"count": 0})

        # Act — resolve находит атрибут, его значение — 0
        result = state.resolve("count")

        # Assert — числовой ноль, не None и не default
        assert result == 0
        assert isinstance(result, int)

    def test_resolve_false_value(self) -> None:
        """
        Булев False — это валидное значение, не отсутствие.

        Аналогично нулю: False — falsy, но resolve различает
        "атрибут существует со значением False" и "атрибут не найден".
        """
        # Arrange — state с False
        state = BaseState({"active": False})

        # Act — resolve находит атрибут со значением False
        result = state.resolve("active")

        # Assert — булев False, не None
        assert result is False
