# src/action_machine/adapters/base_route_record.py
"""
BaseRouteRecord — абстрактный frozen-датакласс конфигурации маршрута адаптера.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

BaseRouteRecord хранит конфигурацию одного зарегистрированного маршрута
адаптера. Содержит поля, общие для любого протокола. Протокольно-
специфичные поля определяются в наследниках.

BaseRouteRecord нельзя инстанцировать напрямую — только через наследников.

═══════════════════════════════════════════════════════════════════════════════
АВТОИЗВЛЕЧЕНИЕ ТИПОВ ИЗ ACTION
═══════════════════════════════════════════════════════════════════════════════

params_type и result_type ВСЕГДА извлекаются автоматически из generic-
параметров BaseAction[P, R] при создании записи. Разработчик никогда
не указывает их вручную. Это обеспечивает единый источник правды:
типы определены в классе действия и не дублируются.

Извлечение выполняется функцией ``extract_action_types(action_class)``,
которая обходит ``__orig_bases__`` в MRO класса и находит запись вида
``BaseAction[P, R]``, где P и R — конкретные типы (не TypeVar).

Результат извлечения кешируется в приватных полях ``_cached_params_type``
и ``_cached_result_type`` через ``object.__setattr__`` (обход frozen).
Это гарантирует, что ``extract_action_types()`` вызывается ровно один
раз при создании записи, а не при каждом обращении к свойствам.

═══════════════════════════════════════════════════════════════════════════════
ОПЦИОНАЛЬНЫЕ ПОЛЯ
═══════════════════════════════════════════════════════════════════════════════

    request_model : type | None
        Модель входящего запроса на протокольном уровне. Если None —
        используется params_type (типы совпадают, маппер не нужен).
        Если указана и отличается от params_type — params_mapper обязателен.

    response_model : type | None
        Модель ответа на протокольном уровне. Если None — используется
        result_type. Если указана и отличается от result_type —
        result_mapper обязателен.

    params_mapper : Callable[[request_model], params_type] | None
        Преобразование протокольного запроса в параметры действия.
        Обязателен если request_model указан и отличается от params_type.

    result_mapper : Callable[[result_type], response_model] | None
        Преобразование результата действия в протокольный ответ.
        Обязателен если response_model указан и отличается от result_type.

═══════════════════════════════════════════════════════════════════════════════
ВАЛИДАЦИЯ ИНВАРИАНТОВ
═══════════════════════════════════════════════════════════════════════════════

При создании экземпляра (в __post_init__) проверяются инварианты:

1. Нельзя создать экземпляр BaseRouteRecord напрямую → TypeError.

2. action_class должен быть подклассом BaseAction → TypeError.

3. Из action_class должны извлекаться P и R → TypeError если не удалось.

4. Если request_model указан, отличается от params_type, и params_mapper
   не указан → ValueError.

5. Если response_model указан, отличается от result_type, и result_mapper
   не указан → ValueError.

═══════════════════════════════════════════════════════════════════════════════
КЕШИРОВАНИЕ ИЗВЛЕЧЁННЫХ ТИПОВ
═══════════════════════════════════════════════════════════════════════════════

Frozen dataclass не позволяет записывать атрибуты через ``self.attr = val``.
Для кеширования результата ``extract_action_types()`` используется
``object.__setattr__(self, "_cached_params_type", p_type)`` — тот же
приём, что в ``ReadableMixin.resolve()`` для ``_resolve_cache`` и в
pydantic frozen-моделях. Это обход frozen на этапе инициализации,
а не нарушение контракта: после ``__post_init__`` кешированные значения
никогда не изменяются.

═══════════════════════════════════════════════════════════════════════════════
ВЫЧИСЛЯЕМЫЕ СВОЙСТВА
═══════════════════════════════════════════════════════════════════════════════

    params_type : type
        Тип параметров действия (P из BaseAction[P, R]).
        Читает из кеша _cached_params_type.

    result_type : type
        Тип результата действия (R из BaseAction[P, R]).
        Читает из кеша _cached_result_type.

    effective_request_model : type
        Фактическая модель запроса: request_model если указан,
        иначе params_type.

    effective_response_model : type
        Фактическая модель ответа: response_model если указан,
        иначе result_type.

═══════════════════════════════════════════════════════════════════════════════
АРХИТЕКТУРА НАСЛЕДОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    BaseRouteRecord (frozen, нельзя инстанцировать)
        │
        │  Поля: action_class, request_model, response_model,
        │  params_mapper, result_mapper
        │  Кеш: _cached_params_type, _cached_result_type
        │  Свойства: params_type, result_type,
        │  effective_request_model, effective_response_model
        │
        ├── FastAPIRouteRecord (frozen)
        │       Поля: method, path, tags, summary, ...
        │
        ├── MCPRouteRecord (frozen)
        │       Поля: tool_name, description, ...
        │
        └── GRPCRouteRecord (frozen)
                Поля: service_name, method_name, ...

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ (ЧЕРЕЗ КОНКРЕТНЫЙ АДАПТЕР)
═══════════════════════════════════════════════════════════════════════════════

    # Минимум — request_model == params_type:
    adapter.post("/orders/create", CreateOrderAction)

    # request_model отличается — нужен params_mapper:
    adapter.get("/orders/list", ListOrdersAction,
                request_model=ListOrdersRequest,
                params_mapper=map_list_request)

    # Оба отличаются — нужны оба маппера:
    adapter.get("/orders/{id}", GetOrderAction,
                request_model=GetRequest,
                response_model=GetResponse,
                params_mapper=map_get_request,
                result_mapper=map_get_response)
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, get_args, get_origin

from action_machine.core.base_action import BaseAction

# ═════════════════════════════════════════════════════════════════════════════
# Извлечение generic-параметров P и R из BaseAction[P, R]
# ═════════════════════════════════════════════════════════════════════════════


def extract_action_types(action_class: type) -> tuple[type, type]:
    """
    Извлекает типы P (params) и R (result) из BaseAction[P, R].

    Обходит ``__orig_bases__`` текущего класса и всех родителей в MRO.
    Ищет запись вида ``BaseAction[P, R]``, где P и R — конкретные типы
    (не TypeVar).

    Аргументы:
        action_class: класс действия (наследник BaseAction).

    Возвращает:
        Кортеж (params_type, result_type).

    Исключения:
        TypeError: если не удалось извлечь generic-параметры.
                   Это означает, что класс объявлен как BaseAction
                   без конкретных типов (например, ``class MyAction(BaseAction): ...``
                   вместо ``class MyAction(BaseAction[MyParams, MyResult]): ...``).
    """
    for klass in action_class.__mro__:
        for base in getattr(klass, "__orig_bases__", ()):
            origin = get_origin(base)
            if origin is BaseAction:
                args = get_args(base)
                if len(args) >= 2 and isinstance(args[0], type) and isinstance(args[1], type):
                    return args[0], args[1]

    raise TypeError(
        f"Не удалось извлечь generic-параметры P и R из {action_class.__name__}. "
        f"Класс действия должен быть объявлен как "
        f"BaseAction[ConcreteParams, ConcreteResult], например: "
        f"class {action_class.__name__}(BaseAction[MyParams, MyResult]): ..."
    )


# ═════════════════════════════════════════════════════════════════════════════
# BaseRouteRecord
# ═════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class BaseRouteRecord:
    """
    Абстрактный frozen-датакласс конфигурации одного маршрута адаптера.

    Содержит поля, общие для любого протокола. Протокольно-специфичные
    поля определяются в наследниках.

    Frozen — после создания ни одно поле изменить нельзя.

    Нельзя инстанцировать напрямую — только через конкретных наследников.

    params_type и result_type извлекаются из action_class один раз
    в __post_init__, кешируются в _cached_params_type/_cached_result_type
    и доступны через вычисляемые свойства.

    Атрибуты (поля dataclass):
        action_class : type[BaseAction]
            Класс действия ActionMachine. Обязательный.

        request_model : type | None
            Модель входящего запроса. Если None — используется params_type.

        response_model : type | None
            Модель ответа. Если None — используется result_type.

        params_mapper : Callable | None
            Преобразование request_model → params_type.
            Обязателен если request_model указан и отличается от params_type.

        result_mapper : Callable | None
            Преобразование result_type → response_model.
            Обязателен если response_model указан и отличается от result_type.

    Кешированные атрибуты (создаются в __post_init__ через object.__setattr__):
        _cached_params_type : type
            Кеш P из BaseAction[P, R]. Читается через свойство params_type.

        _cached_result_type : type
            Кеш R из BaseAction[P, R]. Читается через свойство result_type.
    """

    # ── Обязательное поле ──────────────────────────────────────────────

    action_class: type[BaseAction[Any, Any]]

    # ── Опциональные поля ──────────────────────────────────────────────

    request_model: type | None = None
    response_model: type | None = None
    params_mapper: Callable[..., Any] | None = None
    result_mapper: Callable[..., Any] | None = None

    # ── Валидация и кеширование ────────────────────────────────────────

    def __post_init__(self) -> None:
        """
        Проверяет инварианты и кеширует извлечённые типы.

        Выполняется в строгом порядке:

        1. Запрет прямого инстанцирования BaseRouteRecord.

        2. Проверка action_class — подкласс BaseAction.

        3. Извлечение P и R из action_class. Результат кешируется
           в _cached_params_type и _cached_result_type через
           object.__setattr__ (обход frozen). extract_action_types()
           вызывается ровно один раз.

        4. Валидация params_mapper: обязателен если request_model
           указан и отличается от P.

        5. Валидация result_mapper: обязателен если response_model
           указан и отличается от R.

        Исключения:
            TypeError: прямое создание BaseRouteRecord; action_class
                       не BaseAction; не удалось извлечь P и R.
            ValueError: маппер отсутствует при различающихся типах.
        """
        # ── 1. Запрет прямого инстанцирования ──
        if self.__class__ is BaseRouteRecord:
            raise TypeError(
                "BaseRouteRecord нельзя инстанцировать напрямую. "
                "Создайте конкретный наследник с протокольно-специфичными "
                "полями (FastAPIRouteRecord, MCPRouteRecord и др.)."
            )

        # ── 2. Проверка action_class ──
        if not isinstance(self.action_class, type) or not issubclass(self.action_class, BaseAction):
            raise TypeError(
                f"action_class должен быть подклассом BaseAction, "
                f"получен {self.action_class!r}."
            )

        # ── 3. Извлечение и кеширование P и R ──
        p_type, r_type = extract_action_types(self.action_class)
        object.__setattr__(self, "_cached_params_type", p_type)
        object.__setattr__(self, "_cached_result_type", r_type)

        # ── 4. Валидация params_mapper ──
        if (
            self.request_model is not None
            and self.request_model is not p_type
            and self.params_mapper is None
        ):
            raise ValueError(
                f"request_model ({self.request_model.__name__}) отличается от "
                f"params_type ({p_type.__name__}), но params_mapper не указан. "
                f"Укажите params_mapper для преобразования "
                f"{self.request_model.__name__} → {p_type.__name__}."
            )

        # ── 5. Валидация result_mapper ──
        if (
            self.response_model is not None
            and self.response_model is not r_type
            and self.result_mapper is None
        ):
            raise ValueError(
                f"response_model ({self.response_model.__name__}) отличается от "
                f"result_type ({r_type.__name__}), но result_mapper не указан. "
                f"Укажите result_mapper для преобразования "
                f"{r_type.__name__} → {self.response_model.__name__}."
            )

    # ── Вычисляемые свойства ───────────────────────────────────────────

    @property
    def params_type(self) -> type:
        """
        Тип параметров действия (P из BaseAction[P, R]).

        Извлекается автоматически из action_class при создании записи
        и кешируется. Не указывается разработчиком вручную.

        Возвращает:
            type — класс параметров (наследник BaseParams).
        """
        return self._cached_params_type  # type: ignore[attr-defined, no-any-return]

    @property
    def result_type(self) -> type:
        """
        Тип результата действия (R из BaseAction[P, R]).

        Извлекается автоматически из action_class при создании записи
        и кешируется. Не указывается разработчиком вручную.

        Возвращает:
            type — класс результата (наследник BaseResult).
        """
        return self._cached_result_type  # type: ignore[attr-defined, no-any-return]

    @property
    def effective_request_model(self) -> type:
        """
        Фактическая модель входящего запроса.

        Если request_model указан — возвращает его.
        Если None — возвращает params_type (типы совпадают).

        Используется адаптером для десериализации входящих данных
        и генерации протокольной schema (OpenAPI, JSON Schema).

        Возвращает:
            type — модель запроса.
        """
        if self.request_model is not None:
            return self.request_model
        return self.params_type

    @property
    def effective_response_model(self) -> type:
        """
        Фактическая модель ответа.

        Если response_model указан — возвращает его.
        Если None — возвращает result_type (типы совпадают).

        Используется адаптером для сериализации исходящих данных
        и генерации протокольной schema.

        Возвращает:
            type — модель ответа.
        """
        if self.response_model is not None:
            return self.response_model
        return self.result_type
