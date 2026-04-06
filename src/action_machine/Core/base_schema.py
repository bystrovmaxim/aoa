# src/action_machine/core/base_schema.py
"""
BaseSchema — единая базовая схема данных фреймворка ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

BaseSchema — корневой класс для всех структур данных фреймворка. Наследует
pydantic.BaseModel и добавляет два интерфейса поверх стандартных полей:

1. Dict-подобный доступ к полям: obj["key"], "key" in obj, obj.get("key"),
   obj.keys(), obj.values(), obj.items().

2. Dot-path навигация по вложенным объектам: obj.resolve("user.user_id")
   обходит цепочку вложенных BaseSchema/dict/объектов и возвращает
   значение на конце пути.

Все структуры данных, передаваемые между компонентами системы (параметры,
состояние, результат, контекст, информация о пользователе, запросе и среде
выполнения), наследуют от BaseSchema [2].

═══════════════════════════════════════════════════════════════════════════════
ИЕРАРХИЯ НАСЛЕДОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    BaseSchema(BaseModel)
        ├── BaseParams              — frozen=True, extra="forbid"
        ├── BaseState               — frozen=True, extra="allow"
        ├── BaseResult              — frozen=True, extra="forbid"
        ├── UserInfo                — frozen=True, extra="forbid"
        ├── RequestInfo             — frozen=True, extra="forbid"
        ├── RuntimeInfo             — frozen=True, extra="forbid"
        └── Context                 — frozen=True, extra="forbid"

═══════════════════════════════════════════════════════════════════════════════
ПРИНЦИПЫ
═══════════════════════════════════════════════════════════════════════════════

1. ВСЁ FROZEN. Каждый наследник неизменяем после создания. Единственный
   способ «изменить» — создать новый экземпляр [2].

2. ВСЁ FORBID (кроме BaseState). Произвольные поля запрещены. Расширение
   структуры — только через наследование с явно объявленными полями.
   BaseState использует extra="allow" для динамических полей конвейера [2].

3. ЕДИНЫЙ ИНТЕРФЕЙС. Dict-подобный доступ и dot-path навигация доступны
   на любой схеме. Один базовый класс вместо отдельных Protocol и Mixin [2].

4. PYDANTIC-НАТИВНОСТЬ. Валидация типов при создании, JSON Schema через
   model_json_schema(), сериализация через model_dump(), совместимость
   с FastAPI — из коробки [2].

═══════════════════════════════════════════════════════════════════════════════
DICT-ПОДОБНЫЙ ИНТЕРФЕЙС
═══════════════════════════════════════════════════════════════════════════════

    schema = MySchema(name="test", value=42)

    schema["name"]              → "test"           __getitem__
    "name" in schema            → True              __contains__
    schema.get("missing", 0)    → 0                 get
    list(schema.keys())         → ["name", "value"] keys
    list(schema.values())       → ["test", 42]      values
    list(schema.items())        → [("name", "test"), ("value", 42)]  items

Для наследников с extra="allow" (BaseState) методы keys/values/items
возвращают как объявленные, так и динамические extra-поля [2].

═══════════════════════════════════════════════════════════════════════════════
DOT-PATH НАВИГАЦИЯ
═══════════════════════════════════════════════════════════════════════════════

    context.resolve("user.user_id")      → context.user.user_id
    params.resolve("address.city")       → params.address.city
    state.resolve("payment.txn_id")      → state.payment.txn_id

Навигация делегируется единому DotPathNavigator из модуля core.navigation.
На каждом шаге навигатор выбирает стратегию по типу текущего объекта:

    - BaseSchema → __getitem__
    - LogScope   → __getitem__
    - dict       → прямой доступ по ключу
    - любой объект → getattr

Если на любом шаге значение не найдено — возвращается default (None).

═══════════════════════════════════════════════════════════════════════════════
ИСПОЛЬЗОВАНИЕ В TYPE-HINTS
═══════════════════════════════════════════════════════════════════════════════

    def process(data: BaseSchema) -> None: ...       # любая схема
    def read_only(data: BaseParams) -> None: ...     # иммутабельные параметры
    def with_state(data: BaseState) -> None: ...     # состояние конвейера

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    from pydantic import Field
    from action_machine.core.base_schema import BaseSchema

    class Address(BaseSchema):
        city: str = Field(description="Город")
        zip_code: str = Field(description="Индекс")

    class OrderParams(BaseSchema):
        user_id: str = Field(description="ID пользователя")
        address: Address = Field(description="Адрес доставки")

    params = OrderParams(
        user_id="user_123",
        address=Address(city="Moscow", zip_code="101000"),
    )

    params["user_id"]                    # → "user_123"
    params.resolve("address.city")       # → "Moscow"
    list(params.keys())                  # → ["user_id", "address"]
    params.model_dump()                  # → {"user_id": "user_123", "address": {...}}
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from action_machine.core.navigation import _SENTINEL, DotPathNavigator


class BaseSchema(BaseModel):
    """
    Базовая pydantic-схема с dict-подобным доступом к полям
    и dot-path навигацией по вложенным объектам.

    Все структуры данных фреймворка наследуют этот класс.
    Наследники определяют политику мутабельности (frozen)
    и допустимости произвольных полей (extra) через model_config.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )

    # ─── dict-подобное чтение ─────────────────────────────────────────

    def __getitem__(self, key: str) -> object:
        """
        Доступ к полю по ключу: schema["field_name"].

        Работает для объявленных полей и для extra-полей (если extra="allow").

        Аргументы:
            key: имя поля.

        Возвращает:
            Значение поля.

        Исключения:
            KeyError: если поле с таким именем не существует.
        """
        try:
            return getattr(self, key)
        except AttributeError:
            raise KeyError(key) from None

    def __contains__(self, key: str) -> bool:
        """
        Проверка наличия поля: "field_name" in schema.

        Проверяет как объявленные поля (model_fields), так и
        динамические extra-поля (__pydantic_extra__).

        Аргументы:
            key: имя поля.

        Возвращает:
            True если поле существует.
        """
        if key in self.__class__.model_fields:
            return True
        extra = self.__pydantic_extra__
        if extra and key in extra:
            return True
        return False

    def get(self, key: str, default: object = None) -> object:
        """
        Получение значения поля с fallback на default.

        Аналог dict.get(key, default).

        Аргументы:
            key: имя поля.
            default: значение, возвращаемое при отсутствии поля.

        Возвращает:
            Значение поля или default.
        """
        return getattr(self, key, default)

    def keys(self) -> list[str]:
        """
        Список имён всех полей.

        Включает объявленные поля (model_fields) и динамические
        extra-поля (для наследников с extra="allow").

        Возвращает:
            list[str] — имена полей.
        """
        names = list(self.__class__.model_fields.keys())
        extra = self.__pydantic_extra__
        if extra:
            names.extend(extra.keys())
        return names

    def values(self) -> list[object]:
        """
        Список значений всех полей.

        Порядок соответствует порядку keys().

        Возвращает:
            list[object] — значения полей.
        """
        return [getattr(self, k) for k in self.keys()]

    def items(self) -> list[tuple[str, object]]:
        """
        Список пар (имя, значение) для всех полей.

        Порядок соответствует порядку keys().

        Возвращает:
            list[tuple[str, object]] — пары (ключ, значение).
        """
        return [(k, getattr(self, k)) for k in self.keys()]

    # ─── dot-path навигация ───────────────────────────────────────────

    def resolve(self, dotpath: str, default: object = None) -> object:
        """
        Разрешает dot-path строку, обходя вложенные объекты по цепочке.

        Делегирует навигацию единому DotPathNavigator, который на каждом
        шаге выбирает стратегию по типу текущего объекта:
            - BaseSchema → __getitem__ (dict-подобный доступ).
            - LogScope   → __getitem__ (dict-подобный доступ scope).
            - dict       → прямой доступ по ключу.
            - любой объект → getattr.

        Если на любом шаге цепочки значение не найдено, возвращает
        default без выброса исключения. Поля со значением None
        возвращаются корректно — default используется только при
        отсутствии атрибута.

        Аргументы:
            dotpath: строка вида "user.user_id" или "address.city".
            default: значение, возвращаемое если путь не удалось
                     разрешить. По умолчанию None.

        Возвращает:
            Найденное значение или default.

        Примеры:
            context.resolve("user.user_id")     → "agent_123"
            context.resolve("user.missing")     → None
            context.resolve("user.missing", "") → ""
            context.resolve("user.field_none")  → None  (поле существует)
        """
        result = DotPathNavigator.navigate(self, dotpath)
        if result is _SENTINEL:
            return default
        return result
