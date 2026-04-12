# src/action_machine/contrib/fastapi/adapter.py
"""
FastApiAdapter — HTTP-адаптер для ActionMachine на базе FastAPI.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

FastApiAdapter превращает Action в HTTP-эндпоинты FastAPI. Один вызов
протокольного methodа (post, get, put, delete, patch) = один эндпоинт.
Все протокольные methodы возвращают self для поддержки fluent chain:

    app = adapter \\
        .get("/api/v1/ping", PingAction, tags=["system"]) \\
        .post("/api/v1/orders", CreateOrderAction, tags=["orders"]) \\
        .build()

OpenAPI-документация генерируется автоматически из метаданных, которые
уже есть в коде: описания полей из ``Field(description=...)``, ограничения
из ``Field(gt=0, min_length=3, pattern=...)``, summary из ``@meta``,
теги из аргумента ``tags`` при регистрации.

═══════════════════════════════════════════════════════════════════════════════
ОБЯЗАТЕЛЬНАЯ АУТЕНТИФИКАЦИЯ
═══════════════════════════════════════════════════════════════════════════════

Параметр auth_coordinator обязателен (наследуется от BaseAdapter).
Разработчик не может «забыть» подключить аутентификацию — это error
компиляции (TypeError при auth_coordinator=None), а не молчаливый баг
в production. Для открытых API используется NoAuthCoordinator:

    from action_machine.auth import NoAuthCoordinator

    adapter = FastApiAdapter(
        machine=machine,
        auth_coordinator=NoAuthCoordinator(),
    )

═══════════════════════════════════════════════════════════════════════════════
КОНВЕНЦИЯ ИМЕНОВАНИЯ МАППЕРОВ
═══════════════════════════════════════════════════════════════════════════════

Каждый маппер назван по тому, что он ВОЗВРАЩАЕТ:

    params_mapper   → возвращает params   (преобразует request → params)
    response_mapper → возвращает response (преобразует result  → response)

═══════════════════════════════════════════════════════════════════════════════
СТРАТЕГИИ ГЕНЕРАЦИИ ENDPOINT
═══════════════════════════════════════════════════════════════════════════════

Адаптер использует три стратегии генерации endpoint в зависимости от
HTTP-methodа и наличия полей у модели parameters:

1. POST/PUT/PATCH с непустыми Params — параметры передаются в JSON body.
   FastAPI автоматически валидирует body по Pydantic-модели.

2. GET/DELETE с непустыми Params — параметры передаются как Query
   параметры. Если URL содержит path-параметры (например, {order_id}),
   FastAPI извлекает их из пути, остальные — из query string.

3. Любой method с пустыми Params (без полей) — endpoint не принимает
   body и query parameters. Пустой экземпляр Params создаётся внутри
   handler.

═══════════════════════════════════════════════════════════════════════════════
ОБРАБОТКА ОШИБОК
═══════════════════════════════════════════════════════════════════════════════

Exception handlers регистрируются на уровне FastAPI-приложения:

    AuthorizationError      → HTTP 403 {"detail": "..."}
    ValidationFieldError    → HTTP 422 {"detail": "..."}

Необработанные исключения перехватываются через middleware, которое
оборачивает каждый запрос в try/except и возвращает 500 при любой
ошибке, не пойманной выше.

═══════════════════════════════════════════════════════════════════════════════
HEALTH CHECK
═══════════════════════════════════════════════════════════════════════════════

Эндпоинт ``GET /health`` добавляется автоматически при ``build()``.
Returns ``{"status": "ok"}``.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.auth import NoAuthCoordinator
    from action_machine.contrib.fastapi import FastApiAdapter

    adapter = FastApiAdapter(
        machine=machine,
        auth_coordinator=NoAuthCoordinator(),
        title="Orders API",
        version="0.1.0",
    )

    app = adapter \\
        .post("/api/v1/orders", CreateOrderAction, tags=["orders"]) \\
        .get("/api/v1/orders/{order_id}", GetOrderAction, tags=["orders"]) \\
        .get("/api/v1/ping", PingAction, tags=["system"]) \\
        .build()
"""

from __future__ import annotations

import inspect
import re
from collections.abc import Callable
from typing import Any, Self

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response as StarletteResponse

from action_machine.adapters.base_adapter import BaseAdapter
from action_machine.context.context import Context
from action_machine.core.action_product_machine import ActionProductMachine
from action_machine.core.base_action import BaseAction
from action_machine.core.exceptions import AuthorizationError, ValidationFieldError
from action_machine.metadata.gate_coordinator import GateCoordinator
from action_machine.resource_managers.base_resource_manager import BaseResourceManager

from .route_record import FastApiRouteRecord

# ═════════════════════════════════════════════════════════════════════════════
# Вспомогательные функции модульного уровня
# ═════════════════════════════════════════════════════════════════════════════

_PATH_PARAM_PATTERN: re.Pattern[str] = re.compile(r"\{(\w+)\}")


def _get_meta_description(action_class: type) -> str:
    """
    Извлекает description из ``@meta`` действия.

    Используется для автоматического заполнения summary эндпоинта,
    если разработчик не указал его явно при регистрации маршрута.

    Args:
        action_class: класс действия.

    Returns:
        str — description из @meta или пустая строка.
    """
    meta_info = getattr(action_class, "_meta_info", None)
    if meta_info and isinstance(meta_info, dict):
        return str(meta_info.get("description", ""))
    return ""


def _get_model_fields(model: type) -> dict[str, Any]:
    """
    Returns словарь полей Pydantic-модели.

    Для Pydantic BaseModel использует model_fields.
    Для других типов возвращает пустой словарь.

    Args:
        model: класс модели (Pydantic BaseModel или другой тип).

    Returns:
        dict — словарь {имя_поля: FieldInfo} или пустой словарь.
    """
    if isinstance(model, type) and issubclass(model, BaseModel):
        return model.model_fields
    return {}


def _extract_path_params(path: str) -> set[str]:
    """
    Извлекает имена path-parameters из URL-шаблона.

    Args:
        path: URL-путь с параметрами вида {param_name}.

    Returns:
        set[str] — множество имён path-parameters.
    """
    return set(_PATH_PARAM_PATTERN.findall(path))


def _has_body_method(method: str) -> bool:
    """
    Определяет, поддерживает ли HTTP-method тело запроса (body).

    POST, PUT, PATCH — поддерживают body.
    GET, DELETE — не поддерживают body.

    Args:
        method: HTTP-method в верхнем регистре.

    Returns:
        True если method поддерживает body.
    """
    return method in ("POST", "PUT", "PATCH")


# ═════════════════════════════════════════════════════════════════════════════
# Фабрики endpoint-функций
# ═════════════════════════════════════════════════════════════════════════════


def _make_endpoint_with_body(
    record: FastApiRouteRecord,
    machine: ActionProductMachine,
    auth_coordinator: Any,
    connections_factory: Callable[..., dict[str, BaseResourceManager]] | None,
) -> Callable[..., Any]:
    """
    Создаёт endpoint для methodов с JSON body (POST, PUT, PATCH).

    Параметр ``body`` аннотирован конкретным Pydantic-классом.
    FastAPI автоматически валидирует тело запроса и генерирует
    OpenAPI schema.

    Args:
        record: конфигурация маршрута.
        machine: машина выполнения действий.
        auth_coordinator: координатор аутентификации (AuthCoordinator
                          или NoAuthCoordinator). Обязательный.
        connections_factory: фабрика соединений (или None).

    Returns:
        Async-функцию для передачи в ``app.add_api_route()``.
    """
    req_model = record.effective_request_model
    has_params_mapper = record.params_mapper is not None
    has_response_mapper = record.response_mapper is not None

    async def endpoint(request: Request, body: Any) -> Any:
        if has_params_mapper:
            params = record.params_mapper(body)  # type: ignore[misc]
        else:
            params = body

        context = await auth_coordinator.process(request)
        if context is None:
            context = Context()

        connections = None
        if connections_factory is not None:
            connections = connections_factory()

        action = record.action_class()
        result = await machine.run(context, action, params, connections)

        if has_response_mapper:
            return record.response_mapper(result)  # type: ignore[misc]
        return result

    sig_params = [
        inspect.Parameter("request", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=Request),
        inspect.Parameter("body", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=req_model),
    ]
    endpoint.__signature__ = inspect.Signature(sig_params)  # type: ignore[attr-defined]

    return endpoint


def _make_endpoint_with_query(
    record: FastApiRouteRecord,
    machine: ActionProductMachine,
    auth_coordinator: Any,
    connections_factory: Callable[..., dict[str, BaseResourceManager]] | None,
) -> Callable[..., Any]:
    """
    Создаёт endpoint для GET/DELETE с параметрами из query string и path.

    Каждое поле Pydantic-модели Params становится отдельным параметром
    endpoint-функции. FastAPI определяет по аннотациям, какие параметры
    извлекать из path (если имя совпадает с {param} в URL), а какие —
    из query string.

    Args:
        record: конфигурация маршрута.
        machine: машина выполнения действий.
        auth_coordinator: координатор аутентификации. Обязательный.
        connections_factory: фабрика соединений (или None).

    Returns:
        Async-функцию для передачи в ``app.add_api_route()``.
    """
    req_model = record.effective_request_model
    has_params_mapper = record.params_mapper is not None
    has_response_mapper = record.response_mapper is not None
    model_fields = _get_model_fields(req_model)
    path_params = _extract_path_params(record.path)

    async def endpoint(request: Request, **kwargs: Any) -> Any:
        body = req_model(**kwargs)

        if has_params_mapper:
            params = record.params_mapper(body)  # type: ignore[misc]
        else:
            params = body

        context = await auth_coordinator.process(request)
        if context is None:
            context = Context()

        connections = None
        if connections_factory is not None:
            connections = connections_factory()

        action = record.action_class()
        result = await machine.run(context, action, params, connections)

        if has_response_mapper:
            return record.response_mapper(result)  # type: ignore[misc]
        return result

    sig_params = [
        inspect.Parameter("request", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=Request),
    ]

    for field_name, field_info in model_fields.items():
        annotation = field_info.annotation if field_info.annotation is not None else str

        if field_name in path_params:
            if field_info.default is not None and not field_info.is_required():
                sig_params.append(inspect.Parameter(
                    field_name, inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    annotation=annotation, default=field_info.default,
                ))
            else:
                sig_params.append(inspect.Parameter(
                    field_name, inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    annotation=annotation,
                ))
        else:
            default = field_info.default if not field_info.is_required() else inspect.Parameter.empty
            sig_params.append(inspect.Parameter(
                field_name, inspect.Parameter.POSITIONAL_OR_KEYWORD,
                annotation=annotation, default=default,
            ))

    endpoint.__signature__ = inspect.Signature(sig_params)  # type: ignore[attr-defined]

    return endpoint


def _make_endpoint_no_params(
    record: FastApiRouteRecord,
    machine: ActionProductMachine,
    auth_coordinator: Any,
    connections_factory: Callable[..., dict[str, BaseResourceManager]] | None,
) -> Callable[..., Any]:
    """
    Создаёт endpoint для действий с пустыми Params (без полей).

    Endpoint не принимает body и query parameters. Пустой экземпляр
    Params создаётся внутри handler.

    Args:
        record: конфигурация маршрута.
        machine: машина выполнения действий.
        auth_coordinator: координатор аутентификации. Обязательный.
        connections_factory: фабрика соединений (или None).

    Returns:
        Async-функцию для передачи в ``app.add_api_route()``.
    """
    req_model = record.effective_request_model
    has_params_mapper = record.params_mapper is not None
    has_response_mapper = record.response_mapper is not None

    async def endpoint(request: Request) -> Any:
        body = req_model()

        if has_params_mapper:
            params = record.params_mapper(body)  # type: ignore[misc]
        else:
            params = body

        context = await auth_coordinator.process(request)
        if context is None:
            context = Context()

        connections = None
        if connections_factory is not None:
            connections = connections_factory()

        action = record.action_class()
        result = await machine.run(context, action, params, connections)

        if has_response_mapper:
            return record.response_mapper(result)  # type: ignore[misc]
        return result

    return endpoint


def _make_endpoint(
    record: FastApiRouteRecord,
    machine: ActionProductMachine,
    auth_coordinator: Any,
    connections_factory: Callable[..., dict[str, BaseResourceManager]] | None,
) -> Callable[..., Any]:
    """
    Фабрика endpoint-функций для FastAPI.

    Выбирает стратегию генерации endpoint на основе HTTP-methodа
    и наличия полей у модели parameters:

    1. Пустая модель (нет полей) → endpoint без parameters.
    2. POST/PUT/PATCH с полями → endpoint с JSON body.
    3. GET/DELETE с полями → endpoint с query/path параметрами.

    Args:
        record: конфигурация маршрута.
        machine: машина выполнения действий.
        auth_coordinator: координатор аутентификации. Обязательный.
        connections_factory: фабрика соединений (или None).

    Returns:
        Async-функцию, пригодную для передачи в ``app.add_api_route()``.
    """
    model_fields = _get_model_fields(record.effective_request_model)

    if not model_fields:
        return _make_endpoint_no_params(record, machine, auth_coordinator, connections_factory)

    if _has_body_method(record.method):
        return _make_endpoint_with_body(record, machine, auth_coordinator, connections_factory)

    return _make_endpoint_with_query(record, machine, auth_coordinator, connections_factory)


# ═════════════════════════════════════════════════════════════════════════════
# Middleware
# ═════════════════════════════════════════════════════════════════════════════


class _CatchAllErrorsMiddleware(BaseHTTPMiddleware):
    """
    Middleware для перехвата необработанных исключений.

    Оборачивает каждый запрос в try/except и гарантирует возврат HTTP 500
    при любой непойманной ошибке.
    """

    async def dispatch(
        self, request: StarletteRequest, call_next: Callable[..., Any],
    ) -> StarletteResponse:
        try:
            response: StarletteResponse = await call_next(request)
            return response
        except Exception:
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"},
            )


# ═════════════════════════════════════════════════════════════════════════════
# Class адаптера
# ═════════════════════════════════════════════════════════════════════════════


class FastApiAdapter(BaseAdapter[FastApiRouteRecord]):
    """
    HTTP-адаптер для ActionMachine на базе FastAPI.

    Наследует BaseAdapter[FastApiRouteRecord]. Предоставляет протокольные
    methodы post(), get(), put(), delete(), patch() для регистрации
    HTTP-эндпоинтов. Все протокольные methodы возвращают self для поддержки
    fluent chain. Метод build() завершает цепочку и создаёт FastAPI-приложение.

    Параметр auth_coordinator обязателен (наследуется от BaseAdapter).
    Для открытых API используется NoAuthCoordinator().

    Атрибуты:
        _title : str
            Заголовок API для OpenAPI. Отображается в Swagger UI.

        _version : str
            Версия API для OpenAPI.

        _description : str
            Описание API для OpenAPI. Поддерживает Markdown.
    """

    def __init__(
        self,
        machine: ActionProductMachine,
        auth_coordinator: Any,
        connections_factory: Callable[..., dict[str, BaseResourceManager]] | None = None,
        *,
        gate_coordinator: GateCoordinator | None = None,
        title: str = "ActionMachine API",
        version: str = "0.1.0",
        description: str = "",
    ) -> None:
        """
        Инициализирует FastAPI-адаптер.

        Args:
            machine: машина выполнения действий. Обязательный параметр.
            auth_coordinator: координатор аутентификации. Обязательный параметр.
                              Для открытых API используйте NoAuthCoordinator().
                              None не допускается — TypeError.
            connections_factory: фабрика соединений. Если None —
                                 connections не передаются.
            gate_coordinator: явный ``GateCoordinator``; по умолчанию
                              ``machine.gate_coordinator``.
            title: заголовок API для OpenAPI/Swagger UI.
            version: версия API для OpenAPI.
            description: описание API для OpenAPI. Поддерживает Markdown.
        """
        super().__init__(
            machine=machine,
            auth_coordinator=auth_coordinator,
            connections_factory=connections_factory,
            gate_coordinator=gate_coordinator,
        )
        self._title: str = title
        self._version: str = version
        self._description: str = description

    # ─────────────────────────────────────────────────────────────────────
    # Свойства
    # ─────────────────────────────────────────────────────────────────────

    @property
    def title(self) -> str:
        """Заголовок API для OpenAPI."""
        return self._title

    @property
    def version(self) -> str:
        """Версия API для OpenAPI."""
        return self._version

    @property
    def api_description(self) -> str:
        """Описание API для OpenAPI."""
        return self._description

    # ─────────────────────────────────────────────────────────────────────
    # Внутренний method регистрации (fluent)
    # ─────────────────────────────────────────────────────────────────────

    def _register(
        self,
        method: str,
        path: str,
        action_class: type[BaseAction[Any, Any]],
        request_model: type | None = None,
        response_model: type | None = None,
        params_mapper: Callable[..., Any] | None = None,
        response_mapper: Callable[..., Any] | None = None,
        tags: list[str] | None = None,
        summary: str = "",
        description: str = "",
        operation_id: str | None = None,
        deprecated: bool = False,
    ) -> Self:
        """
        Создаёт FastApiRouteRecord, добавляет его в _routes и возвращает self.

        Если ``summary`` пуст — автоматически подставляется description
        из ``@meta`` действия.
        """
        effective_summary = summary or _get_meta_description(action_class)

        record = FastApiRouteRecord(
            action_class=action_class,
            request_model=request_model,
            response_model=response_model,
            params_mapper=params_mapper,
            response_mapper=response_mapper,
            method=method,
            path=path,
            tags=tuple(tags or ()),
            summary=effective_summary,
            description=description,
            operation_id=operation_id,
            deprecated=deprecated,
        )
        return self._add_route(record)

    # ─────────────────────────────────────────────────────────────────────
    # Протокольные methodы (fluent — возвращают Self)
    # ─────────────────────────────────────────────────────────────────────

    def post(
        self,
        path: str,
        action_class: type[BaseAction[Any, Any]],
        request_model: type | None = None,
        response_model: type | None = None,
        params_mapper: Callable[..., Any] | None = None,
        response_mapper: Callable[..., Any] | None = None,
        tags: list[str] | None = None,
        summary: str = "",
        description: str = "",
        operation_id: str | None = None,
        deprecated: bool = False,
    ) -> Self:
        """Регистрирует POST-эндпоинт. Returns self для fluent chain."""
        return self._register(
            "POST", path, action_class, request_model, response_model,
            params_mapper, response_mapper, tags, summary, description,
            operation_id, deprecated,
        )

    def get(
        self,
        path: str,
        action_class: type[BaseAction[Any, Any]],
        request_model: type | None = None,
        response_model: type | None = None,
        params_mapper: Callable[..., Any] | None = None,
        response_mapper: Callable[..., Any] | None = None,
        tags: list[str] | None = None,
        summary: str = "",
        description: str = "",
        operation_id: str | None = None,
        deprecated: bool = False,
    ) -> Self:
        """Регистрирует GET-эндпоинт. Returns self для fluent chain."""
        return self._register(
            "GET", path, action_class, request_model, response_model,
            params_mapper, response_mapper, tags, summary, description,
            operation_id, deprecated,
        )

    def put(
        self,
        path: str,
        action_class: type[BaseAction[Any, Any]],
        request_model: type | None = None,
        response_model: type | None = None,
        params_mapper: Callable[..., Any] | None = None,
        response_mapper: Callable[..., Any] | None = None,
        tags: list[str] | None = None,
        summary: str = "",
        description: str = "",
        operation_id: str | None = None,
        deprecated: bool = False,
    ) -> Self:
        """Регистрирует PUT-эндпоинт. Returns self для fluent chain."""
        return self._register(
            "PUT", path, action_class, request_model, response_model,
            params_mapper, response_mapper, tags, summary, description,
            operation_id, deprecated,
        )

    def delete(
        self,
        path: str,
        action_class: type[BaseAction[Any, Any]],
        request_model: type | None = None,
        response_model: type | None = None,
        params_mapper: Callable[..., Any] | None = None,
        response_mapper: Callable[..., Any] | None = None,
        tags: list[str] | None = None,
        summary: str = "",
        description: str = "",
        operation_id: str | None = None,
        deprecated: bool = False,
    ) -> Self:
        """Регистрирует DELETE-эндпоинт. Returns self для fluent chain."""
        return self._register(
            "DELETE", path, action_class, request_model, response_model,
            params_mapper, response_mapper, tags, summary, description,
            operation_id, deprecated,
        )

    def patch(
        self,
        path: str,
        action_class: type[BaseAction[Any, Any]],
        request_model: type | None = None,
        response_model: type | None = None,
        params_mapper: Callable[..., Any] | None = None,
        response_mapper: Callable[..., Any] | None = None,
        tags: list[str] | None = None,
        summary: str = "",
        description: str = "",
        operation_id: str | None = None,
        deprecated: bool = False,
    ) -> Self:
        """Регистрирует PATCH-эндпоинт. Returns self для fluent chain."""
        return self._register(
            "PATCH", path, action_class, request_model, response_model,
            params_mapper, response_mapper, tags, summary, description,
            operation_id, deprecated,
        )

    # ─────────────────────────────────────────────────────────────────────
    # Построение FastAPI-приложения
    # ─────────────────────────────────────────────────────────────────────

    def build(self) -> FastAPI:
        """
        Создаёт FastAPI-приложение из зарегистрированных маршрутов.

        Порядок инициализации:
        1. Создание FastAPI-приложения с метаданными OpenAPI.
        2. Добавление middleware для перехвата необработанных исключений.
        3. Регистрация exception handlers.
        4. Регистрация health check эндпоинта GET /health.
        5. Генерация и регистрация endpoint для каждого маршрута.

        Returns:
            FastAPI — готовое приложение.
        """
        app = FastAPI(
            title=self._title,
            version=self._version,
            description=self._description,
        )

        app.add_middleware(_CatchAllErrorsMiddleware)
        self._register_exception_handlers(app)
        self._register_health_check(app)

        for record in self._routes:
            self._register_endpoint(app, record)

        return app

    # ─────────────────────────────────────────────────────────────────────
    # Генерация эндпоинтов
    # ─────────────────────────────────────────────────────────────────────

    def _register_endpoint(self, app: FastAPI, record: FastApiRouteRecord) -> None:
        """
        Генерирует и регистрирует один async endpoint из FastApiRouteRecord.
        """
        endpoint = _make_endpoint(
            record=record,
            machine=self._machine,
            auth_coordinator=self._auth_coordinator,
            connections_factory=self._connections_factory,
        )

        app.add_api_route(
            path=record.path,
            endpoint=endpoint,
            methods=[record.method],
            response_model=record.effective_response_model,
            tags=list(record.tags) if record.tags else None,
            summary=record.summary or None,
            description=record.description or None,
            operation_id=record.operation_id,
            deprecated=record.deprecated or None,
        )

    # ─────────────────────────────────────────────────────────────────────
    # Exception handlers
    # ─────────────────────────────────────────────────────────────────────

    @staticmethod
    def _register_exception_handlers(app: FastAPI) -> None:
        """
        Регистрирует обработчики исключений ActionMachine на уровне приложения.

            AuthorizationError   → HTTP 403 Forbidden
            ValidationFieldError → HTTP 422 Unprocessable Entity
        """

        @app.exception_handler(AuthorizationError)
        async def handle_authorization_error(
            request: Request, exc: AuthorizationError,
        ) -> JSONResponse:
            return JSONResponse(
                status_code=403,
                content={"detail": str(exc)},
            )

        @app.exception_handler(ValidationFieldError)
        async def handle_validation_error(
            request: Request, exc: ValidationFieldError,
        ) -> JSONResponse:
            return JSONResponse(
                status_code=422,
                content={"detail": str(exc)},
            )

    # ─────────────────────────────────────────────────────────────────────
    # Health check
    # ─────────────────────────────────────────────────────────────────────

    @staticmethod
    def _register_health_check(app: FastAPI) -> None:
        """Добавляет ``GET /health → {"status": "ok"}``."""

        @app.get("/health", tags=["system"])
        async def health_check() -> dict[str, str]:
            return {"status": "ok"}
