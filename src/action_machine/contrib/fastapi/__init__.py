# src/action_machine/contrib/fastapi/__init__.py
"""
FastAPI-адаптер для ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Превращает Action в HTTP-эндпоинты FastAPI. Разработчик пишет
``adapter.post("/orders", CreateOrderAction)`` — адаптер генерирует
async handler, подключает валидацию, обработку ошибок и OpenAPI-документацию.

Description полей, constraints, examples — всё из Pydantic-моделей
Params/Result и декоратора ``@meta``.

═══════════════════════════════════════════════════════════════════════════════
УСТАНОВКА
═══════════════════════════════════════════════════════════════════════════════

    pip install action-machine[fastapi]

═══════════════════════════════════════════════════════════════════════════════
КОМПОНЕНТЫ
═══════════════════════════════════════════════════════════════════════════════

- FastApiAdapter — конкретный адаптер, наследующий BaseAdapter[FastApiRouteRecord].
  Предоставляет протокольные методы post(), get(), put(), delete(), patch().
  Метод build() создаёт FastAPI-приложение из зарегистрированных маршрутов.

- FastApiRouteRecord — frozen-датакласс маршрута с HTTP-специфичными полями:
  method, path, tags, summary, description, operation_id, deprecated.

═══════════════════════════════════════════════════════════════════════════════
БЫСТРЫЙ СТАРТ
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.core.action_product_machine import ActionProductMachine
    from action_machine.core.gate_coordinator import GateCoordinator
    from action_machine.contrib.fastapi import FastApiAdapter

    coordinator = GateCoordinator()
    machine = ActionProductMachine(mode="production", coordinator=coordinator)

    adapter = FastApiAdapter(
        machine=machine,
        title="Orders API",
        version="0.1.0",
    )

    # Минимум — request_model совпадает с params_type:
    adapter.post("/api/v1/orders", CreateOrderAction, tags=["orders"])

    # request_model отличается — нужен params_mapper:
    adapter.get("/api/v1/orders", ListOrdersAction,
                request_model=ListOrdersRequest,
                params_mapper=map_list_request,
                tags=["orders"])

    # Без аутентификации:
    adapter.get("/api/v1/ping", PingAction, tags=["system"])

    app = adapter.build()

    # Запуск:
    # uvicorn myapp:app --reload

═══════════════════════════════════════════════════════════════════════════════
АВТОМАТИЧЕСКАЯ ГЕНЕРАЦИЯ OPENAPI
═══════════════════════════════════════════════════════════════════════════════

OpenAPI schema генерируется из метаданных, которые уже есть в коде:

- Описания полей → из ``Field(description="...")`` в Params и Result.
- Ограничения → из ``Field(gt=0, min_length=3, pattern=...)`` в Params.
- Примеры → из ``Field(examples=["..."])`` в Params и Result.
- Summary эндпоинта → из ``@meta(description="...")`` действия.
- Tags → из аргумента ``tags=[...]`` при регистрации маршрута.

Swagger UI доступен на ``http://host:port/docs``.
ReDoc доступен на ``http://host:port/redoc``.

═══════════════════════════════════════════════════════════════════════════════
ОБРАБОТКА ОШИБОК
═══════════════════════════════════════════════════════════════════════════════

Адаптер регистрирует exception handlers на уровне FastAPI-приложения:

    AuthorizationError      → HTTP 403 Forbidden
    ValidationFieldError    → HTTP 422 Unprocessable Entity
    Exception (любое)       → HTTP 500 Internal Server Error

Каждый ответ содержит JSON body ``{"detail": "сообщение ошибки"}``.

═══════════════════════════════════════════════════════════════════════════════
HEALTH CHECK
═══════════════════════════════════════════════════════════════════════════════

Эндпоинт ``GET /health`` добавляется автоматически при ``build()``.
Возвращает ``{"status": "ok"}``. Используется для liveness probe
в Kubernetes, мониторинга и health check балансировщиков нагрузки.
"""

try:
    import fastapi  # noqa: F401
except ImportError:
    raise ImportError(
        "Для использования action_machine.contrib.fastapi "
        "установите зависимость: pip install action-machine[fastapi]"
    ) from None

from .adapter import FastApiAdapter
from .route_record import FastApiRouteRecord

__all__ = [
    "FastApiAdapter",
    "FastApiRouteRecord",
]
