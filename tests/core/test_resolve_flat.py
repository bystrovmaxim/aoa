# tests/core/test_resolve_flat.py
"""
Тесты BaseSchema.resolve() для плоских полей (без вложенности).

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Метод resolve(dotpath, default) — основной механизм навигации по данным
в системе логирования ActionMachine. Шаблоны вида {%context.user.user_id},
{%state.total}, {%params.amount} разрешаются через resolve().

Этот файл тестирует самый простой случай: плоские поля без вложенности.
resolve("user_id") для одного сегмента пути эквивалентно __getitem__("user_id")
с обработкой KeyError → возврат default.

Более сложные случаи (вложенные объекты, словари, смешанные типы)
покрыты в test_base_schema_resolve.py.

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
    - UserInfo (BaseSchema, frozen, forbid) — плоские поля.
    - BaseState (BaseSchema, frozen, allow) — динамические extra-поля.
    - BaseParams (BaseSchema, frozen, forbid) — объявленные pydantic-поля.

Falsy-значения:
    - Пустая строка "" — валидное значение, не отсутствие.
    - Числовой ноль 0 — валидное значение, не отсутствие.
    - Булев False — валидное значение, не отсутствие.
"""

from pydantic import Field

from action_machine.intents.context.user_info import UserInfo
from action_machine.model.base_params import BaseParams
from action_machine.model.base_state import BaseState
from tests.domain_model.roles import AdminRole, AgentRole, ManagerRole, UserRole

# ═════════════════════════════════════════════════════════════════════════════
# Базовый доступ к плоским полям
# ═════════════════════════════════════════════════════════════════════════════


class TestResolveFlatBasic:
    """Базовый доступ к плоским полям через resolve()."""

    def test_resolve_string_field(self) -> None:
        """
        resolve("user_id") возвращает строковое значение поля.

        UserInfo наследует BaseSchema. resolve разбивает "user_id"
        по точкам → ["user_id"], вызывает __getitem__("user_id")
        → getattr(self, "user_id").
        """
        # Arrange — UserInfo с user_id="agent_007"
        user = UserInfo(user_id="agent_007", roles=(AgentRole,))

        # Act — resolve по одному сегменту, без вложенности
        result = user.resolve("user_id")

        # Assert — строковое значение из поля user.user_id
        assert result == "agent_007"

    def test_resolve_list_field(self) -> None:
        """
        resolve("roles") возвращает кортеж типов ролей целиком.

        resolve не поддерживает индексацию по элементам tuple (roles.0).
        Для получения элемента нужно сначала получить кортеж,
        потом обращаться к элементу в Python-коде.
        """
        # Arrange — UserInfo с двумя ролями
        user = UserInfo(user_id="42", roles=(AdminRole, UserRole))

        # Act — resolve возвращает весь кортеж
        result = user.resolve("roles")

        # Assert — кортеж из двух типов, тип сохранён
        assert result == (AdminRole, UserRole)
        assert isinstance(result, tuple)

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
        resolve находит поле через __getitem__ и возвращает его значение
        как есть, не заменяя на default.
        """
        # Arrange — user_id явно установлен в None
        user = UserInfo(user_id=None)

        # Act — resolve находит поле, его значение — None
        result = user.resolve("user_id")

        # Assert — возвращён None, а не default
        assert result is None

    def test_resolve_none_value_ignores_default(self) -> None:
        """
        None с default — default НЕ подставляется.

        Ключевое отличие от отсутствия поля: если поле существует
        и равно None, default не применяется. Default применяется
        только когда __getitem__ бросает KeyError (поле не найдено).
        """
        # Arrange — user_id явно равен None
        user = UserInfo(user_id=None)

        # Act — resolve с default="fallback"
        result = user.resolve("user_id", default="fallback")

        # Assert — возвращён None, а не "fallback",
        # потому что поле существует (хоть и равно None)
        assert result is None


# ═════════════════════════════════════════════════════════════════════════════
# Разные типы объектов с BaseSchema
# ═════════════════════════════════════════════════════════════════════════════


class TestResolveFlatDifferentObjects:
    """resolve() работает единообразно на разных наследниках BaseSchema."""

    def test_resolve_on_base_state(self) -> None:
        """
        resolve() на BaseState — динамические extra-поля.

        BaseState — pydantic-модель с extra="allow". Динамические поля,
        переданные через kwargs при создании, доступны через __getitem__
        и resolve так же, как объявленные поля.
        """
        # Arrange — BaseState с двумя динамическими полями (kwargs)
        state = BaseState(txn_id="TXN-001", total=1500.0)

        # Act — resolve плоских полей
        txn_id = state.resolve("txn_id")
        total = state.resolve("total")

        # Assert — значения из extra-полей
        assert txn_id == "TXN-001"
        assert total == 1500.0

    def test_resolve_on_pydantic_params(self) -> None:
        """
        resolve() на pydantic BaseParams — объявленные поля модели.

        BaseParams наследует BaseSchema (pydantic BaseModel).
        resolve обращается к значениям через __getitem__ → getattr,
        который работает одинаково для всех наследников BaseSchema.
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
        resolve() на UserInfo — frozen BaseSchema с двумя полями.

        UserInfo содержит user_id и roles. Поле extra удалено —
        расширение через наследование с явно объявленными полями.
        """
        # Arrange — UserInfo с обоими полями
        user = UserInfo(
            user_id="test_user",
            roles=(AdminRole, ManagerRole),
        )

        # Act — resolve каждого плоского поля
        user_id = user.resolve("user_id")
        roles = user.resolve("roles")

        # Assert — каждое поле возвращает своё значение с правильным типом
        assert user_id == "test_user"
        assert roles == (AdminRole, ManagerRole)

    def test_resolve_empty_string_field(self) -> None:
        """
        Пустая строка "" — это валидное значение, не отсутствие.
        resolve возвращает "", а не default.
        """
        # Arrange — user_id = пустая строка
        user = UserInfo(user_id="")

        # Act — resolve находит поле, его значение — ""
        result = user.resolve("user_id")

        # Assert — пустая строка, не None и не default
        assert result == ""
        assert isinstance(result, str)

    def test_resolve_zero_value(self) -> None:
        """
        Числовой ноль 0 — это валидное значение, не отсутствие.
        resolve возвращает 0, а не default. Ноль — falsy в Python,
        но resolve различает «поле найдено со значением 0»
        и «поле не найдено → default».
        """
        # Arrange — state с нулевым значением (kwargs)
        state = BaseState(count=0)

        # Act — resolve находит поле, его значение — 0
        result = state.resolve("count")

        # Assert — числовой ноль, не None и не default
        assert result == 0
        assert isinstance(result, int)

    def test_resolve_false_value(self) -> None:
        """
        Булев False — это валидное значение, не отсутствие.
        Аналогично нулю: False — falsy, но resolve различает
        «поле существует со значением False» и «поле не найдено».
        """
        # Arrange — state с False (kwargs)
        state = BaseState(active=False)

        # Act — resolve находит поле со значением False
        result = state.resolve("active")

        # Assert — булев False, не None
        assert result is False
