# src/action_machine/contrib/fastapi/route_record.py
"""
FastApiRouteRecord — frozen-датакласс маршрута для FastAPI-адаптера.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

FastApiRouteRecord — конкретный наследник BaseRouteRecord с HTTP-специфичными
полями. Хранит полную конфигурацию одного HTTP-эндпоинта: метод, путь, теги,
описание, operation_id, deprecated. Используется FastApiAdapter при build()
для генерации FastAPI-маршрутов.

═══════════════════════════════════════════════════════════════════════════════
HTTP-СПЕЦИФИЧНЫЕ ПОЛЯ
═══════════════════════════════════════════════════════════════════════════════

    method : str
        HTTP-метод: GET, POST, PUT, DELETE, PATCH. Приводится к верхнему
        регистру при валидации. Допустимые значения определены в множестве
        ``_ALLOWED_METHODS``. По умолчанию "POST".

    path : str
        URL-путь эндпоинта. Непустая строка, начинающаяся с ``/``.
        Поддерживает path-параметры FastAPI: ``/orders/{order_id}``.
        По умолчанию "/".

    tags : tuple[str, ...]
        Теги для группировки в OpenAPI/Swagger UI. Каждый тег
        отображается как отдельная секция в документации.
        По умолчанию пустой кортеж.

    summary : str
        Краткое описание эндпоинта для OpenAPI. Отображается рядом
        с путём в Swagger UI. Если пустая строка — FastApiAdapter
        подставит description из ``@meta`` действия.
        По умолчанию пустая строка.

    description : str
        Развёрнутое описание эндпоинта для OpenAPI. Отображается
        при раскрытии эндпоинта в Swagger UI. Поддерживает Markdown.
        По умолчанию пустая строка.

    operation_id : str | None
        Уникальный идентификатор операции в OpenAPI. Если None —
        FastAPI генерирует автоматически из имени функции.
        По умолчанию None.

    deprecated : bool
        Флаг устаревшего эндпоинта. В Swagger UI отображается
        зачёркнутым. По умолчанию False.

═══════════════════════════════════════════════════════════════════════════════
НАСЛЕДОВАНИЕ ОТ BaseRouteRecord
═══════════════════════════════════════════════════════════════════════════════

Наследует от BaseRouteRecord все общие поля: action_class, request_model,
response_model, params_mapper, response_mapper. Наследует все инварианты:

- action_class должен быть подклассом BaseAction.
- params_type и result_type извлекаются автоматически из BaseAction[P, R].
- Если request_model указан и отличается от params_type — params_mapper
  обязателен.
- Если response_model указан и отличается от result_type — response_mapper
  обязателен.

В ``__post_init__`` выполняются HTTP-специфичные проверки:

- method из допустимого набора {GET, POST, PUT, DELETE, PATCH}.
- path непустой и начинается с ``/``.

═══════════════════════════════════════════════════════════════════════════════
КОНВЕНЦИЯ ИМЕНОВАНИЯ МАППЕРОВ
═══════════════════════════════════════════════════════════════════════════════

Каждый маппер назван по тому, что он ВОЗВРАЩАЕТ:

    params_mapper   → возвращает params   (преобразует request → params)
    response_mapper → возвращает response (преобразует result  → response)

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР СОЗДАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    # Минимум:
    record = FastApiRouteRecord(
        action_class=CreateOrderAction,
        path="/api/v1/orders",
    )

    # Полный набор:
    record = FastApiRouteRecord(
        action_class=CreateOrderAction,
        request_model=CreateOrderRequest,
        response_model=CreateOrderResponse,
        params_mapper=map_request_to_params,
        response_mapper=map_result_to_response,
        method="POST",
        path="/api/v1/orders",
        tags=("orders", "create"),
        summary="Создание заказа",
        description="Создаёт новый заказ в системе.",
        operation_id="create_order",
        deprecated=False,
    )
"""

from __future__ import annotations

from dataclasses import dataclass

from action_machine.adapters.base_route_record import BaseRouteRecord

# Допустимые HTTP-методы.
_ALLOWED_METHODS: frozenset[str] = frozenset({
    "GET",
    "POST",
    "PUT",
    "DELETE",
    "PATCH",
})


@dataclass(frozen=True)
class FastApiRouteRecord(BaseRouteRecord):
    """
    Frozen-датакласс маршрута для FastAPI-адаптера.

    Наследует BaseRouteRecord (action_class, request_model, response_model,
    params_mapper, response_mapper) и добавляет HTTP-специфичные поля.

    Frozen — после создания ни одно поле изменить нельзя.

    Валидация в ``__post_init__``:
    - Вызывает ``super().__post_init__()`` для проверки инвариантов
      BaseRouteRecord (action_class, маппинг, извлечение P и R).
    - Проверяет method из допустимого набора.
    - Проверяет path непустой и начинается с ``/``.

    Атрибуты (HTTP-специфичные поля):
        method : str
            HTTP-метод. По умолчанию "POST".

        path : str
            URL-путь эндпоинта. По умолчанию "/".

        tags : tuple[str, ...]
            Теги для OpenAPI. По умолчанию ().

        summary : str
            Краткое описание для OpenAPI. По умолчанию "".

        description : str
            Развёрнутое описание для OpenAPI. По умолчанию "".

        operation_id : str | None
            Уникальный ID операции в OpenAPI. По умолчанию None.

        deprecated : bool
            Флаг устаревшего эндпоинта. По умолчанию False.
    """

    # ── HTTP-специфичные поля ──────────────────────────────────────────

    method: str = "POST"
    path: str = "/"
    tags: tuple[str, ...] = ()
    summary: str = ""
    description: str = ""
    operation_id: str | None = None
    deprecated: bool = False

    # ── Валидация ──────────────────────────────────────────────────────

    def __post_init__(self) -> None:
        """
        Проверяет HTTP-специфичные инварианты после создания экземпляра.

        Порядок:

        1. Вызов ``super().__post_init__()`` — проверка инвариантов
           BaseRouteRecord (action_class, маппинг, извлечение P и R,
           запрет прямого создания BaseRouteRecord).

        2. Нормализация method: приведение к верхнему регистру.
           Frozen dataclass не позволяет ``self.method = ...``,
           поэтому используется ``object.__setattr__``.

        3. Проверка method из допустимого набора.

        4. Проверка path: непустой и начинается с ``/``.

        Исключения:
            TypeError: от BaseRouteRecord (action_class не BaseAction,
                       не удалось извлечь P и R).
            ValueError: от BaseRouteRecord (маппер отсутствует при
                        различающихся типах); method недопустимый;
                        path пустой или не начинается с ``/``.
        """
        # ── 1. Инварианты BaseRouteRecord ──
        super().__post_init__()

        # ── 2. Нормализация method ──
        normalized_method = self.method.upper()
        object.__setattr__(self, "method", normalized_method)

        # ── 3. Проверка method ──
        if normalized_method not in _ALLOWED_METHODS:
            allowed = ", ".join(sorted(_ALLOWED_METHODS))
            raise ValueError(
                f"method должен быть одним из: {allowed}. "
                f"Получен: '{self.method}'."
            )

        # ── 4. Проверка path ──
        if not self.path or not self.path.strip():
            raise ValueError(
                "path не может быть пустой строкой. "
                "Укажите путь эндпоинта, например '/api/v1/orders'."
            )

        if not self.path.startswith("/"):
            raise ValueError(
                f"path должен начинаться с '/'. "
                f"Получен: '{self.path}'. "
                f"Укажите путь, например '/{self.path}'."
            )
