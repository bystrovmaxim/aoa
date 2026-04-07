# src/action_machine/domain/entity.py
"""
BaseEntity — абстрактный базовый класс для всех сущностей доменной модели.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

BaseEntity — единый стандарт для всех сущностей домена в системе
ActionMachine. Определяет структуру бизнес-объекта: его поля, жизненные
циклы (Lifecycle) и правила доступа к данным.

Сущность — это внутреннее представление бизнес-объекта (заказ, клиент,
товар), а не объект для передачи через API. Для внешнего API используются
отдельные Params и Result (как в Action). В простых случаях model_dump()
работает, но для production API рекомендуется создавать DTO.

Модель не знает про базы данных, HTTP, файлы или любой другой внешний мир.
Это чистое ядро в терминах гексагональной архитектуры. Один и тот же
OrderEntity может читаться из PostgreSQL, MongoDB, REST API или мока —
это забота ресурсного менеджера (адаптера), а не модели.

═══════════════════════════════════════════════════════════════════════════════
ИЕРАРХИЯ НАСЛЕДОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    BaseSchema(BaseModel)           — dict-подобный доступ, dot-path навигация
        └── BaseEntity(ABC)         — frozen=True, extra="forbid"
                ├── EntityGateHost          — разрешает @entity
                └── DescribedFieldsGateHost — обязательность description у полей

BaseEntity наследует BaseSchema, получая:
- Dict-подобный доступ к полям: entity["field"], "field" in entity.
- Dot-path навигацию: entity.resolve("address.city").
- Сериализацию через model_dump().
- Валидацию типов при создании через Pydantic.

═══════════════════════════════════════════════════════════════════════════════
FROZEN-СЕМАНТИКА
═══════════════════════════════════════════════════════════════════════════════

Все сущности неизменяемы после создания (frozen=True). Это гарантирует:

- Предсказуемость: аспекты и менеджеры не могут случайно изменить
  бизнес-объект.
- Безопасность: один и тот же экземпляр сущности безопасно передаётся
  во все аспекты, плагины и обработчики ошибок.
- Консистентность: данные сущности на любом этапе конвейера совпадают
  с тем, что было загружено из хранилища.

Единственный способ «изменить» сущность — создать новый экземпляр:

    updated = order.model_copy(update={"status": "shipped"})

═══════════════════════════════════════════════════════════════════════════════
СТРОГАЯ СТРУКТУРА (extra="forbid")
═══════════════════════════════════════════════════════════════════════════════

Сущность содержит ровно те поля, которые объявлены в конкретном
наследнике. Произвольные поля запрещены. Это защита от опечаток,
случайных данных и разрастания структуры.

═══════════════════════════════════════════════════════════════════════════════
ОБЯЗАТЕЛЬНЫЕ ОПИСАНИЯ ПОЛЕЙ
═══════════════════════════════════════════════════════════════════════════════

Каждое поле сущности обязано иметь описание через Field(description="...").
Это контролируется DescribedFieldsGateHost. Координатор сущностей при
сборке метаданных проверяет: если класс наследует DescribedFieldsGateHost
и содержит pydantic-поля — каждое поле обязано иметь непустой description.

Описание — это структурное метаданное, которое попадёт в ArchiMate-диаграмму,
OCEL-схему и автогенерированную документацию. Модель без описаний — это код,
а не спецификация.

═══════════════════════════════════════════════════════════════════════════════
ОБЯЗАТЕЛЬНЫЙ ДЕКОРАТОР @entity
═══════════════════════════════════════════════════════════════════════════════

Каждая конкретная сущность обязана быть декорирована @entity:

    @entity(description="Заказ клиента", domain=ShopDomain)
    class OrderEntity(BaseEntity):
        ...

Декоратор записывает _entity_info = {"description": ..., "domain": ...}
на класс. Координатор сущностей читает этот атрибут при сборке метаданных.
Без @entity координатор не увидит сущность.

═══════════════════════════════════════════════════════════════════════════════
ЖИЗНЕННЫЕ ЦИКЛЫ (LIFECYCLE)
═══════════════════════════════════════════════════════════════════════════════

Сущность может содержать любое количество полей типа Lifecycle или
ни одного. Каждый Lifecycle — декларативный конечный автомат, описывающий
допустимые состояния и переходы бизнес-объекта.

Поля Lifecycle объявляются как атрибуты уровня класса (ClassVar),
а не как pydantic-поля. Они не участвуют в сериализации, валидации
и создании экземпляров — это метаданные структуры, а не данные.

Координатор сущностей автоматически обнаруживает все поля типа Lifecycle
и проверяет каждый на восемь правил целостности при сборке метаданных.

═══════════════════════════════════════════════════════════════════════════════
ИНВАРИАНТ ИМЕНОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

Каждый класс, наследующий BaseEntity (прямо или косвенно), обязан иметь
суффикс "Entity" в имени. Проверка выполняется в __init_subclass__
при определении класса. Нарушение → NamingSuffixError.

Примеры:
    class OrderEntity(BaseEntity):     ← OK
    class CustomerEntity(BaseEntity):  ← OK
    class Order(BaseEntity):           ← NamingSuffixError

═══════════════════════════════════════════════════════════════════════════════
ЧАСТИЧНАЯ ЗАГРУЗКА ЧЕРЕЗ partial()
═══════════════════════════════════════════════════════════════════════════════

Из хранилища часто читаются только нужные поля (SELECT id, amount FROM ...).
Classmethod partial() создаёт экземпляр без Pydantic-валидации через
model_construct(). При обращении к незагруженному полю — FieldNotLoadedError
с перечислением загруженных полей.

Это НЕ lazy-loading. Никаких скрытых запросов к хранилищу. Поле либо
загружено при создании, либо нет. Обращение к незагруженному полю —
немедленная ошибка с информативным сообщением.

Частичная загрузка реализуется через переопределение __getattr__:
Pydantic вызывает __getattr__ только для атрибутов, НЕ найденных
через обычный механизм (object.__getattribute__). Если поле было
передано в partial() — оно записано в __dict__ экземпляра через
model_construct() и найдётся через __getattribute__, минуя __getattr__.
Если поле НЕ было передано — __getattribute__ не найдёт его и вызовет
__getattr__, где мы проверяем, является ли запрашиваемый атрибут
объявленным полем модели (model_fields), и если да — выбрасываем
FieldNotLoadedError. Для атрибутов, не являющихся полями модели,
поведение не меняется.

Метка _partial_instance и множество _loaded_fields записываются через
object.__setattr__ для обхода frozen-ограничения Pydantic.

    # Полная загрузка — все обязательные поля, Pydantic-валидация:
    order = OrderEntity(id="ORD-001", amount=100.0, status="new")

    # Частичная загрузка — только нужные поля, без валидации:
    order = OrderEntity.partial(id="ORD-001", amount=100.0)
    order.id      # → "ORD-001" ✅
    order.status  # → FieldNotLoadedError

═══════════════════════════════════════════════════════════════════════════════
СЕРИАЛИЗАЦИЯ
═══════════════════════════════════════════════════════════════════════════════

Сериализация выполняется через model_dump() из Pydantic. Для частично
загруженных сущностей model_dump() вернёт только загруженные поля
(через параметр include).

Для внешнего API рекомендуется создавать отдельные DTO, потому что:
- partial() может вызвать FieldNotLoadedError при сериализации.
- Контейнеры связей (этап 3) сериализуются со внутренней структурой.
- Глубина вложенности связей не контролируется.

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    from pydantic import Field
    from action_machine.domain import BaseEntity, BaseDomain, Lifecycle
    from action_machine.domain.entity_decorator import entity

    class ShopDomain(BaseDomain):
        name = "shop"
        description = "Интернет-магазин"

    @entity(description="Заказ клиента", domain=ShopDomain)
    class OrderEntity(BaseEntity):
        lifecycle = (
            Lifecycle("Жизненный цикл заказа")
            .state("new", "Новый").to("confirmed", "cancelled").initial()
            .state("confirmed", "Подтверждён").to("shipped").intermediate()
            .state("shipped", "Отправлен").to("delivered").intermediate()
            .state("delivered", "Доставлен").final()
            .state("cancelled", "Отменён").final()
        )

        id: str = Field(description="Идентификатор заказа")
        amount: float = Field(description="Сумма заказа", ge=0)
        status: str = Field(description="Текущий статус заказа")
        currency: str = Field(default="RUB", description="Код валюты ISO 4217")

    # Полная загрузка:
    order = OrderEntity(id="ORD-001", amount=1500.0, status="new")
    order["id"]                  # → "ORD-001"
    order.resolve("amount")      # → 1500.0
    order.model_dump()           # → {"id": "ORD-001", "amount": 1500.0, ...}

    # Частичная загрузка:
    order = OrderEntity.partial(id="ORD-001", amount=1500.0)
    order.id                     # → "ORD-001"
    order.status                 # → FieldNotLoadedError

    # «Изменение» — создание нового экземпляра:
    updated = order.model_copy(update={"status": "confirmed"})
"""

from __future__ import annotations

from abc import ABC
from typing import Any, ClassVar, Self

from pydantic import ConfigDict

from action_machine.core.base_schema import BaseSchema
from action_machine.core.described_fields_gate_host import DescribedFieldsGateHost
from action_machine.core.exceptions import NamingSuffixError
from action_machine.domain.entity_gate_host import EntityGateHost
from action_machine.domain.exceptions import FieldNotLoadedError

# Суффикс, обязательный для всех классов, наследующих BaseEntity.
_REQUIRED_SUFFIX = "Entity"


class BaseEntity(BaseSchema, ABC, EntityGateHost, DescribedFieldsGateHost):
    """
    Абстрактный базовый класс для всех сущностей доменной модели.

    Frozen после создания. Произвольные поля запрещены.
    Каждое поле обязано иметь описание через Field(description="...").

    Наследует dict-подобный доступ и dot-path навигацию от BaseSchema.
    Наследует EntityGateHost (разрешает @entity).
    Наследует DescribedFieldsGateHost (обязательность описаний полей).

    Предоставляет classmethod partial() для частичной загрузки — создание
    экземпляра с подмножеством полей без Pydantic-валидации. Обращение
    к незагруженному полю → FieldNotLoadedError.

    Каждый конкретный наследник обязан:
    1. Иметь суффикс "Entity" в имени класса.
    2. Быть декорирован @entity(description="...", domain=...).
    3. Каждое поле — Field(description="...").

    Атрибуты экземпляра (для частично загруженных сущностей):
        _partial_instance : bool
            True если экземпляр создан через partial(). False для
            полностью загруженных сущностей. Записывается через
            object.__setattr__ для обхода frozen.

        _loaded_fields : frozenset[str]
            Множество имён полей, загруженных при создании через partial().
            Пустой frozenset для полностью загруженных сущностей.
            Записывается через object.__setattr__ для обхода frozen.

    Атрибуты уровня класса:
        _entity_info : dict[str, Any]
            Словарь метаданных, записываемый декоратором @entity.
            Содержит "description" и "domain".
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # Аннотация для mypy (создаётся декоратором @entity)
    _entity_info: ClassVar[dict[str, Any]]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """
        Вызывается Python при создании любого подкласса BaseEntity.

        Проверяет инвариант именования: имя класса обязано заканчиваться
        на "Entity". Нарушение → NamingSuffixError.

        Аргументы:
            **kwargs: аргументы, передаваемые в type.__init_subclass__.

        Исключения:
            NamingSuffixError: если имя класса не заканчивается на "Entity".
        """
        super().__init_subclass__(**kwargs)

        if not cls.__name__.endswith(_REQUIRED_SUFFIX):
            raise NamingSuffixError(
                f"Класс '{cls.__name__}' наследует BaseEntity, но не имеет "
                f"суффикса '{_REQUIRED_SUFFIX}'. "
                f"Переименуйте в '{cls.__name__}{_REQUIRED_SUFFIX}'."
            )

    @classmethod
    def partial(cls, **kwargs: Any) -> Self:
        """
        Создаёт частично загруженную сущность без Pydantic-валидации.

        Использует model_construct() для создания экземпляра с подмножеством
        полей. Пропускает валидацию типов и обязательность полей — это
        ответственность менеджера, загружающего данные из хранилища.

        После создания записывает метки _partial_instance=True и
        _loaded_fields=frozenset(kwargs.keys()) через object.__setattr__
        для обхода frozen-ограничения Pydantic.

        При обращении к незагруженному полю __getattr__ выбрасывает
        FieldNotLoadedError с информативным сообщением.

        Аргументы:
            **kwargs: загружаемые поля и их значения.
                      Ключи — имена полей сущности.
                      Значения — данные из хранилища.

        Возвращает:
            Self — экземпляр сущности с загруженным подмножеством полей.

        Пример:
            order = OrderEntity.partial(id="ORD-001", amount=1500.0)
            order.id      # → "ORD-001"
            order.status  # → FieldNotLoadedError
        """
        instance = cls.model_construct(**kwargs)
        object.__setattr__(instance, "_partial_instance", True)
        object.__setattr__(instance, "_loaded_fields", frozenset(kwargs.keys()))
        return instance

    def __getattr__(self, name: str) -> Any:
        """
        Перехватывает доступ к незагруженным полям частичных сущностей.

        Pydantic вызывает __getattr__ только для атрибутов, НЕ найденных
        через стандартный object.__getattribute__. Для полностью
        загруженных сущностей все поля записаны в __dict__ экземпляра
        и найдутся через __getattribute__, поэтому __getattr__ не вызывается.

        Для частично загруженных сущностей (created via partial()):
        - Загруженные поля записаны в __dict__ → __getattribute__ найдёт их.
        - Незагруженные поля НЕ записаны → __getattribute__ не найдёт →
          вызовется __getattr__ → проверяем, является ли имя полем модели →
          если да, выбрасываем FieldNotLoadedError.

        Для атрибутов, не являющихся полями модели (методы, свойства,
        внутренние атрибуты Pydantic), поведение стандартное — AttributeError.

        Аргументы:
            name: имя запрашиваемого атрибута.

        Возвращает:
            Никогда не возвращает значение для незагруженных полей.

        Исключения:
            FieldNotLoadedError: если это поле модели и сущность частичная.
            AttributeError: если атрибут не является полем модели.
        """
        # Проверяем, является ли запрашиваемый атрибут полем pydantic-модели
        if name in self.__class__.model_fields:
            # Проверяем, является ли экземпляр частичным
            # Используем object.__getattribute__ для обхода рекурсии
            try:
                is_partial = object.__getattribute__(self, "_partial_instance")
            except AttributeError:
                is_partial = False

            if is_partial:
                loaded = object.__getattribute__(self, "_loaded_fields")
                raise FieldNotLoadedError(
                    field_name=name,
                    entity_class_name=self.__class__.__name__,
                    loaded_fields=loaded,
                )

        # Стандартное поведение для нeполей
        raise AttributeError(
            f"'{self.__class__.__name__}' object has no attribute '{name}'"
        )
