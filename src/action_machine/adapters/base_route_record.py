# src/action_machine/adapters/base_route_record.py
"""
BaseRouteRecord — абстрактный frozen-датакласс конфигурации маршрута адаптера.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

BaseRouteRecord — абстрактный базовый класс для записей маршрутов всех
протокольных адаптеров. Содержит поля, общие для любого протокола
(действие, типы параметров/результата, модели запроса/ответа, мапперы).

Протокольно-специфичные поля (HTTP-метод, путь, теги для FastAPI;
tool_name для MCP; service_name для gRPC) определяются в наследниках.
Это обеспечивает полную типизацию: IDE автодополняет поля конкретного
протокола, mypy проверяет типы, опечатки обнаруживаются статически.

BaseRouteRecord нельзя инстанцировать напрямую — только через наследников.
Попытка создать экземпляр BaseRouteRecord вызывает TypeError.

═══════════════════════════════════════════════════════════════════════════════
ОБЯЗАТЕЛЬНЫЕ ПОЛЯ
═══════════════════════════════════════════════════════════════════════════════

    action_class : type[BaseAction]
        Класс действия ActionMachine. Адаптер создаёт экземпляр этого
        класса при каждом входящем запросе и передаёт в machine.run().

    params_type : type
        Тип параметров действия (generic P из BaseAction[P, R]).
        Наследник BaseParams. Используется адаптером для автоматической
        десериализации тела запроса, когда params_mapper=None.

    result_type : type
        Тип результата действия (generic R из BaseAction[P, R]).
        Наследник BaseResult. Используется адаптером для автоматической
        сериализации ответа, когда result_mapper=None.

    request_model : type
        Модель входящего запроса на протокольном уровне.
        Для FastAPI — pydantic-модель для OpenAPI schema и валидации тела.
        Для MCP — модель для JSON Schema инструмента.
        Адаптер использует эту модель для десериализации входящих данных
        из протокольного формата.

    response_model : type
        Модель ответа на протокольном уровне.
        Для FastAPI — pydantic-модель для OpenAPI response schema.
        Адаптер использует эту модель для сериализации исходящих данных
        в протокольный формат.

═══════════════════════════════════════════════════════════════════════════════
ОПЦИОНАЛЬНЫЕ ПОЛЯ (МАППЕРЫ)
═══════════════════════════════════════════════════════════════════════════════

    params_mapper : Callable[[request_model], params_type] | None
        Функция преобразования протокольного запроса (request_model)
        в параметры действия (params_type).

        Правила:
        - Если params_type is request_model (один и тот же класс) →
          params_mapper ДОЛЖЕН быть None. Адаптер передаёт объект
          напрямую без преобразования.
        - Если params_type is not request_model (разные классы) →
          params_mapper ОБЯЗАТЕЛЕН (Callable). Адаптер вызывает
          params_mapper(request_object) для получения params.

        Пример:
            # params_type == request_model → маппер не нужен:
            params_mapper=None

            # params_type != request_model → маппер обязателен:
            params_mapper=lambda req: OrderParams(
                user_id=req.user_id,
                amount=req.amount,
            )

    result_mapper : Callable[[result_type], response_model] | None
        Функция преобразования результата действия (result_type)
        в протокольный ответ (response_model).

        Правила:
        - Если result_type is response_model → result_mapper ДОЛЖЕН
          быть None. Адаптер передаёт объект напрямую.
        - Если result_type is not response_model → result_mapper
          ОБЯЗАТЕЛЕН (Callable).

        Пример:
            # result_type == response_model → маппер не нужен:
            result_mapper=None

            # result_type != response_model → маппер обязателен:
            result_mapper=lambda res: CreateOrderResponse(
                order_id=res["order_id"],
                status=res["status"],
            )

═══════════════════════════════════════════════════════════════════════════════
ВАЛИДАЦИЯ ИНВАРИАНТОВ
═══════════════════════════════════════════════════════════════════════════════

При создании экземпляра (в __post_init__) проверяются три инварианта:

1. Нельзя создать экземпляр BaseRouteRecord напрямую → TypeError.
   Только конкретные наследники могут быть инстанцированы.

2. Если params_type is not request_model и params_mapper is None →
   ValueError. Невозможно преобразовать запрос в параметры без маппера.

3. Если result_type is not response_model и result_mapper is None →
   ValueError. Невозможно преобразовать результат в ответ без маппера.

Обратные случаи (маппер указан при одинаковых типах) допускаются —
разработчик может захотеть выполнить дополнительную трансформацию
даже при совпадении типов.

═══════════════════════════════════════════════════════════════════════════════
АРХИТЕКТУРА НАСЛЕДОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    BaseRouteRecord (frozen, нельзя инстанцировать)
        │
        │  Общие поля: action_class, params_type, result_type,
        │  request_model, response_model, params_mapper, result_mapper
        │
        ├── FastAPIRouteRecord (frozen)
        │       Поля: method, path, tags, summary, description,
        │       operation_id, deprecated, ...
        │
        ├── MCPRouteRecord (frozen)
        │       Поля: tool_name, description, ...
        │
        └── GRPCRouteRecord (frozen)
                Поля: service_name, method_name, ...

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР КОНКРЕТНОГО НАСЛЕДНИКА
═══════════════════════════════════════════════════════════════════════════════

    @dataclass(frozen=True)
    class FastAPIRouteRecord(BaseRouteRecord):
        method: str = "POST"
        path: str = "/"
        tags: tuple[str, ...] = ()
        summary: str = ""
        description: str = ""
        operation_id: str | None = None
        deprecated: bool = False

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР СОЗДАНИЯ (ЧЕРЕЗ НАСЛЕДНИКА)
═══════════════════════════════════════════════════════════════════════════════

    # Одинаковые типы — маппер не нужен:
    record = FastAPIRouteRecord(
        action_class=PingAction,
        params_type=PingParams,
        result_type=PingResult,
        request_model=PingParams,
        response_model=PingResult,
        method="GET",
        path="/api/v1/ping",
    )

    # Разные типы — маппер обязателен:
    record = FastAPIRouteRecord(
        action_class=CreateOrderAction,
        params_type=OrderParams,
        result_type=OrderResult,
        request_model=CreateOrderRequest,
        response_model=CreateOrderResponse,
        params_mapper=lambda req: OrderParams(
            user_id=req.user_id, amount=req.amount,
        ),
        result_mapper=lambda res: CreateOrderResponse(
            order_id=res["order_id"], status=res["status"],
        ),
        method="POST",
        path="/api/v1/orders",
        tags=("orders",),
        summary="Создание заказа",
    )
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from action_machine.core.base_action import BaseAction


@dataclass(frozen=True)
class BaseRouteRecord:
    """
    Абстрактный frozen-датакласс конфигурации одного маршрута адаптера.

    Содержит поля, общие для любого протокола. Протокольно-специфичные
    поля определяются в наследниках (FastAPIRouteRecord, MCPRouteRecord).

    Frozen — после создания ни одно поле изменить нельзя.

    Нельзя инстанцировать напрямую — попытка создать экземпляр
    BaseRouteRecord (а не наследника) вызывает TypeError.

    Валидация инвариантов выполняется в ``__post_init__``:
    - Прямое создание BaseRouteRecord запрещено.
    - params_mapper обязателен если params_type != request_model.
    - result_mapper обязателен если result_type != response_model.

    Атрибуты:
        action_class : type[BaseAction]
            Класс действия ActionMachine. Адаптер создаёт экземпляр
            при каждом входящем запросе.

        params_type : type
            Тип параметров действия (P из BaseAction[P, R]).
            Наследник BaseParams.

        result_type : type
            Тип результата действия (R из BaseAction[P, R]).
            Наследник BaseResult.

        request_model : type
            Модель входящего запроса на протокольном уровне.

        response_model : type
            Модель ответа на протокольном уровне.

        params_mapper : Callable | None
            Преобразование request_model → params_type.
            None допустим только если params_type is request_model.

        result_mapper : Callable | None
            Преобразование result_type → response_model.
            None допустим только если result_type is response_model.
    """

    # ── Обязательные поля ──────────────────────────────────────────────

    action_class: type[BaseAction[Any, Any]]
    params_type: type
    result_type: type
    request_model: type
    response_model: type

    # ── Опциональные поля (мапперы) ────────────────────────────────────

    params_mapper: Callable[..., Any] | None = None
    result_mapper: Callable[..., Any] | None = None

    # ── Валидация инвариантов ──────────────────────────────────────────

    def __post_init__(self) -> None:
        """
        Проверяет инварианты после создания экземпляра.

        Инварианты:

        1. Прямое создание BaseRouteRecord запрещено. Только конкретные
           наследники могут быть инстанцированы. Проверяется через
           ``self.__class__ is BaseRouteRecord``. Используется ``__class__``
           вместо ``type()`` для соответствия pylint C0123.

        2. Если params_type и request_model — разные классы,
           params_mapper обязателен. Без маппера адаптер не знает,
           как преобразовать протокольный запрос в параметры действия.

        3. Если result_type и response_model — разные классы,
           result_mapper обязателен. Без маппера адаптер не знает,
           как преобразовать результат действия в протокольный ответ.

        Обратные случаи (маппер указан при одинаковых типах) допускаются:
        разработчик может захотеть выполнить дополнительную трансформацию.

        Исключения:
            TypeError: при попытке создать экземпляр BaseRouteRecord напрямую.
            ValueError: если маппер отсутствует при различающихся типах.
        """
        # ── 1. Запрет прямого инстанцирования ──
        if self.__class__ is BaseRouteRecord:
            raise TypeError(
                "BaseRouteRecord нельзя инстанцировать напрямую. "
                "Создайте конкретный наследник с протокольно-специфичными "
                "полями (FastAPIRouteRecord, MCPRouteRecord и др.)."
            )

        # ── 2. Валидация params_mapper ──
        if self.params_type is not self.request_model and self.params_mapper is None:
            raise ValueError(
                f"params_type ({self.params_type.__name__}) и "
                f"request_model ({self.request_model.__name__}) — разные классы, "
                f"но params_mapper не указан. Укажите params_mapper для "
                f"преобразования {self.request_model.__name__} → "
                f"{self.params_type.__name__}."
            )

        # ── 3. Валидация result_mapper ──
        if self.result_type is not self.response_model and self.result_mapper is None:
            raise ValueError(
                f"result_type ({self.result_type.__name__}) и "
                f"response_model ({self.response_model.__name__}) — разные классы, "
                f"но result_mapper не указан. Укажите result_mapper для "
                f"преобразования {self.result_type.__name__} → "
                f"{self.response_model.__name__}."
            )
