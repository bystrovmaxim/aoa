# src/action_machine/contrib/fastapi/adapter.py
"""
FastApiAdapter — HTTP-адаптер для ActionMachine на базе FastAPI.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

FastApiAdapter превращает Action в HTTP-эндпоинты FastAPI. Один вызов
протокольного метода (post, get, put, delete, patch) = один эндпоинт.
Все протокольные методы возвращают self для поддержки fluent chain:

    app = adapter \\
        .get("/api/v1/ping", PingAction, tags=["system"]) \\
        .post("/api/v1/orders", CreateOrderAction, tags=["orders"]) \\
        .build()

OpenAPI-документация генерируется автоматически из метаданных, которые
уже есть в коде: описания полей из ``Field(description=...)``, ограничения
из ``Field(gt=0, min_length=3, pattern=...)``, summary из ``@meta``,
теги из аргумента ``tags`` при регистрации.

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
HTTP-метода и наличия полей у модели параметров:

1. POST/PUT/PATCH с непустыми Params — параметры передаются в JSON body.
   FastAPI автоматически валидирует body по Pydantic-модели.

2. GET/DELETE с непустыми Params — параметры передаются как Query
   параметры. Если URL содержит path-параметры (например, {order_id}),
   FastAPI извлекает их из пути, остальные — из query string.

3. Любой метод с пустыми Params (без полей) — endpoint не принимает
   body и query параметров. Пустой экземпляр Params создаётся внутри
   handler.

Выбор стратегии определяется в ``_make_endpoint`` на основе метода
(record.method) и наличия полей (model_fields) у effective_request_model.

═══════════════════════════════════════════════════════════════════════════════
ГЕНЕРАЦИЯ ENDPOINT С ПРАВИЛЬНОЙ СИГНАТУРОЙ
═══════════════════════════════════════════════════════════════════════════════

FastAPI определяет тип request body по аннотации параметра endpoint-функции.
Замыкание ``async def endpoint(body: req_model)`` не работает, потому что
Pydantic видит ``ForwardRef('req_model')`` вместо реального типа.

Решение: endpoint-функция создаётся фабричной функцией, которая получает
конкретный класс модели как параметр и использует ``inspect.Parameter``
для построения правильной сигнатуры с аннотацией типа, понятной FastAPI
и Pydantic.

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
Возвращает ``{"status": "ok"}``.

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.contrib.fastapi import FastApiAdapter

    adapter = FastApiAdapter(
        machine=machine,
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
from action_machine.auth.auth_coordinator import AuthCoordinator
from action_machine.context.context import Context
from action_machine.core.action_product_machine import ActionProductMachine
from action_machine.core.base_action import BaseAction
from action_machine.core.exceptions import AuthorizationError, ValidationFieldError
from action_machine.resource_managers.base_resource_manager import BaseResourceManager

from .route_record import FastApiRouteRecord

# ═════════════════════════════════════════════════════════════════════════════
# Вспомогательные функции модульного уровня
# ═════════════════════════════════════════════════════════════════════════════

# Регулярное выражение для извлечения path-параметров из URL.
_PATH_PARAM_PATTERN: re.Pattern[str] = re.compile(r"\{(\w+)\}")


def _get_meta_description(action_class: type) -> str:
    """
    Извлекает description из ``@meta`` действия.

    Используется для автоматического заполнения summary эндпоинта,
    если разработчик не указал его явно при регистрации маршрута.

    Аргументы:
        action_class: класс действия.

    Возвращает:
        str — description из @meta или пустая строка.
    """
    meta_info = getattr(action_class, "_meta_info", None)
    if meta_info and isinstance(meta_info, dict):
        return str(meta_info.get("description", ""))
    return ""


def _get_model_fields(model: type) -> dict[str, Any]:
    """
    Возвращает словарь полей Pydantic-модели.

    Для Pydantic BaseModel использует model_fields.
    Для других типов возвращает пустой словарь.

    Аргументы:
        model: класс модели (Pydantic BaseModel или другой тип).

    Возвращает:
        dict — словарь {имя_поля: FieldInfo} или пустой словарь.
    """
    if isinstance(model, type) and issubclass(model, BaseModel):
        return model.model_fields
    return {}


def _extract_path_params(path: str) -> set[str]:
    """
    Извлекает имена path-параметров из URL-шаблона.

    Аргументы:
        path: URL-путь с параметрами вида {param_name}.

    Возвращает:
        set[str] — множество имён path-параметров.

    Пример:
        _extract_path_params("/orders/{order_id}/items/{item_id}")
        → {"order_id", "item_id"}
    """
    return set(_PATH_PARAM_PATTERN.findall(path))


def _has_body_method(method: str) -> bool:
    """
    Определяет, поддерживает ли HTTP-метод тело запроса (body).

    POST, PUT, PATCH — поддерживают body.
    GET, DELETE — не поддерживают body.

    Аргументы:
        method: HTTP-метод в верхнем регистре.

    Возвращает:
        True если метод поддерживает body.
    """
    return method in ("POST", "PUT", "PATCH")


# ═════════════════════════════════════════════════════════════════════════════
# Фабрики endpoint-функций
# ═════════════════════════════════════════════════════════════════════════════


def _make_endpoint_with_body(
    record: FastApiRouteRecord,
    machine: ActionProductMachine,
    auth_coordinator: AuthCoordinator | None,
    connections_factory: Callable[..., dict[str, BaseResourceManager]] | None,
) -> Callable[..., Any]:
    """
    Создаёт endpoint для методов с JSON body (POST, PUT, PATCH).

    Параметр ``body`` аннотирован конкретным Pydantic-классом.
    FastAPI автоматически валидирует тело запроса и генерирует
    OpenAPI schema.

    Аргументы:
        record: конфигурация маршрута.
        machine: машина выполнения действий.
        auth_coordinator: координатор аутентификации (или None).
        connections_factory: фабрика соединений (или None).

    Возвращает:
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

        if auth_coordinator is not None:
            context = await auth_coordinator.process(request)
            if context is None:
                context = Context()
        else:
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
    auth_coordinator: AuthCoordinator | None,
    connections_factory: Callable[..., dict[str, BaseResourceManager]] | None,
) -> Callable[..., Any]:
    """
    Создаёт endpoint для GET/DELETE с параметрами из query string и path.

    Каждое поле Pydantic-модели Params становится отдельным параметром
    endpoint-функции. FastAPI определяет по аннотациям, какие параметры
    извлекать из path (если имя совпадает с {param} в URL), а какие —
    из query string.

    Аргументы:
        record: конфигурация маршрута.
        machine: машина выполнения действий.
        auth_coordinator: координатор аутентификации (или None).
        connections_factory: фабрика соединений (или None).

    Возвращает:
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

        if auth_coordinator is not None:
            context = await auth_coordinator.process(request)
            if context is None:
                context = Context()
        else:
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
    auth_coordinator: AuthCoordinator | None,
    connections_factory: Callable[..., dict[str, BaseResourceManager]] | None,
) -> Callable[..., Any]:
    """
    Создаёт endpoint для действий с пустыми Params (без полей).

    Endpoint не принимает body и query параметров. Пустой экземпляр
    Params создаётся внутри handler.

    Аргументы:
        record: конфигурация маршрута.
        machine: машина выполнения действий.
        auth_coordinator: координатор аутентификации (или None).
        connections_factory: фабрика соединений (или None).

    Возвращает:
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

        if auth_coordinator is not None:
            context = await auth_coordinator.process(request)
            if context is None:
                context = Context()
        else:
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
    auth_coordinator: AuthCoordinator | None,
    connections_factory: Callable[..., dict[str, BaseResourceManager]] | None,
) -> Callable[..., Any]:
    """
    Фабрика endpoint-функций для FastAPI.

    Выбирает стратегию генерации endpoint на основе HTTP-метода
    и наличия полей у модели параметров:

    1. Пустая модель (нет полей) → endpoint без параметров.
    2. POST/PUT/PATCH с полями → endpoint с JSON body.
    3. GET/DELETE с полями → endpoint с query/path параметрами.

    Аргументы:
        record: конфигурация маршрута с action_class, маппингами и моделями.
        machine: машина выполнения действий.
        auth_coordinator: координатор аутентификации (или None).
        connections_factory: фабрика соединений (или None).

    Возвращает:
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

    Стандартный FastAPI ``exception_handler(Exception)`` не перехватывает
    все подклассы Exception в некоторых версиях Starlette. Этот middleware
    оборачивает каждый запрос в try/except и гарантирует возврат HTTP 500
    при любой непойманной ошибке.
    """

    async def dispatch(
        self, request: StarletteRequest, call_next: Callable[..., Any],
    ) -> StarletteResponse:
        """
        Оборачивает обработку запроса в try/except.

        Аргументы:
            request: входящий HTTP-запрос.
            call_next: следующий обработчик в цепочке middleware.

        Возвращает:
            HTTP-ответ от следующего обработчика или JSONResponse 500.
        """
        try:
            response: StarletteResponse = await call_next(request)
            return response
        except Exception:
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"},
            )


# ═════════════════════════════════════════════════════════════════════════════
# Класс адаптера
# ═════════════════════════════════════════════════════════════════════════════


class FastApiAdapter(BaseAdapter[FastApiRouteRecord]):
    """
    HTTP-адаптер для ActionMachine на базе FastAPI.

    Наследует BaseAdapter[FastApiRouteRecord]. Предоставляет протокольные
    методы post(), get(), put(), delete(), patch() для регистрации
    HTTP-эндпоинтов. Все протокольные методы возвращают self для поддержки
    fluent chain. Метод build() завершает цепочку и создаёт FastAPI-приложение.

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
        auth_coordinator: AuthCoordinator | None = None,
        connections_factory: Callable[..., dict[str, BaseResourceManager]] | None = None,
        title: str = "ActionMachine API",
        version: str = "0.1.0",
        description: str = "",
    ) -> None:
        """
        Инициализирует FastAPI-адаптер.

        Аргументы:
            machine: машина выполнения действий. Обязательный параметр.
                     Должен быть экземпляром ActionProductMachine.
            auth_coordinator: координатор аутентификации. Если указан,
                              вызывается для каждого запроса, создаёт Context
                              из данных HTTP-запроса. Если None — Context
                              создаётся пустым.
            connections_factory: фабрика соединений. Если указана, вызывается
                                 перед каждым machine.run() и возвращает
                                 dict[str, BaseResourceManager]. Если None —
                                 connections не передаются.
            title: заголовок API для OpenAPI/Swagger UI. Отображается
                   в верхней части документации. По умолчанию "ActionMachine API".
            version: версия API для OpenAPI. Отображается рядом с заголовком.
                     По умолчанию "0.1.0".
            description: описание API для OpenAPI. Поддерживает Markdown.
                         Отображается под заголовком в Swagger UI.
                         По умолчанию пустая строка.
        """
        super().__init__(
            machine=machine,
            auth_coordinator=auth_coordinator,
            connections_factory=connections_factory,
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
    # Внутренний метод регистрации (fluent)
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

        Аргументы:
            method: HTTP-метод (GET, POST, PUT, DELETE, PATCH).
            path: URL-путь эндпоинта.
            action_class: класс действия.
            request_model: протокольная модель запроса (или None).
            response_model: протокольная модель ответа (или None).
            params_mapper: функция request_model → params_type (или None).
            response_mapper: функция result_type → response_model (или None).
            tags: теги для группировки в OpenAPI (или None).
            summary: краткое описание для OpenAPI (или пустая строка).
            description: развёрнутое описание для OpenAPI (или пустая строка).
            operation_id: уникальный ID операции в OpenAPI (или None).
            deprecated: флаг устаревшего эндпоинта.

        Возвращает:
            Self — текущий экземпляр адаптера для fluent chain.
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
    # Протокольные методы (fluent — возвращают Self)
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
        """
        Регистрирует POST-эндпоинт. Возвращает self для fluent chain.

        POST используется для создания ресурсов. Параметры передаются
        в JSON body запроса. FastAPI автоматически валидирует body
        по Pydantic-модели effective_request_model.

        Аргументы:
            path: URL-путь эндпоинта. Непустая строка, начинающаяся с ``/``.
                  Поддерживает path-параметры: ``/orders/{order_id}``.
            action_class: класс действия (наследник BaseAction[P, R]).
                          P и R извлекаются автоматически из generic-параметров.
            request_model: протокольная модель входящего запроса. Если None —
                           используется params_type (P из BaseAction[P, R]).
                           Если указана и отличается от params_type —
                           params_mapper обязателен.
            response_model: протокольная модель ответа. Если None —
                            используется result_type (R из BaseAction[P, R]).
                            Если указана и отличается от result_type —
                            response_mapper обязателен.
            params_mapper: функция преобразования request_model → params_type.
                           Вызывается перед machine.run() для конвертации
                           протокольного запроса в параметры действия.
                           Назван по тому, что возвращает: params.
                           None если request_model совпадает с params_type.
            response_mapper: функция преобразования result_type → response_model.
                             Вызывается после machine.run() для конвертации
                             результата действия в протокольный ответ.
                             Назван по тому, что возвращает: response.
                             None если response_model совпадает с result_type.
            tags: список тегов для группировки в OpenAPI/Swagger UI.
                  Каждый тег отображается как секция в документации.
                  None или пустой список — без тегов.
            summary: краткое описание эндпоинта для OpenAPI. Отображается
                     рядом с путём в Swagger UI. Пустая строка — адаптер
                     подставит description из ``@meta`` действия.
            description: развёрнутое описание эндпоинта для OpenAPI.
                         Отображается при раскрытии эндпоинта. Поддерживает
                         Markdown. По умолчанию пустая строка.
            operation_id: уникальный идентификатор операции в OpenAPI.
                          None — FastAPI генерирует автоматически.
            deprecated: флаг устаревшего эндпоинта. True — в Swagger UI
                        отображается зачёркнутым. По умолчанию False.

        Возвращает:
            Self — текущий экземпляр адаптера для fluent chain.
        """
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
        """
        Регистрирует GET-эндпоинт. Возвращает self для fluent chain.

        GET используется для чтения ресурсов. Параметры передаются через
        query string и path-параметры. Если URL содержит ``{param_name}``,
        FastAPI извлекает его из пути, остальные поля — из query string.

        Аргументы:
            path: URL-путь эндпоинта с опциональными path-параметрами.
            action_class: класс действия (наследник BaseAction[P, R]).
            request_model: протокольная модель запроса (или None).
            response_model: протокольная модель ответа (или None).
            params_mapper: функция request_model → params_type (или None).
            response_mapper: функция result_type → response_model (или None).
            tags: теги для OpenAPI (или None).
            summary: краткое описание для OpenAPI.
            description: развёрнутое описание для OpenAPI.
            operation_id: уникальный ID операции (или None).
            deprecated: флаг устаревшего эндпоинта.

        Возвращает:
            Self — текущий экземпляр адаптера для fluent chain.
        """
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
        """
        Регистрирует PUT-эндпоинт. Возвращает self для fluent chain.

        PUT используется для полной замены ресурса. Параметры передаются
        в JSON body запроса.

        Аргументы:
            path: URL-путь эндпоинта.
            action_class: класс действия (наследник BaseAction[P, R]).
            request_model: протокольная модель запроса (или None).
            response_model: протокольная модель ответа (или None).
            params_mapper: функция request_model → params_type (или None).
            response_mapper: функция result_type → response_model (или None).
            tags: теги для OpenAPI (или None).
            summary: краткое описание для OpenAPI.
            description: развёрнутое описание для OpenAPI.
            operation_id: уникальный ID операции (или None).
            deprecated: флаг устаревшего эндпоинта.

        Возвращает:
            Self — текущий экземпляр адаптера для fluent chain.
        """
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
        """
        Регистрирует DELETE-эндпоинт. Возвращает self для fluent chain.

        DELETE используется для удаления ресурсов. Параметры передаются
        через query string и path-параметры (аналогично GET).

        Аргументы:
            path: URL-путь эндпоинта.
            action_class: класс действия (наследник BaseAction[P, R]).
            request_model: протокольная модель запроса (или None).
            response_model: протокольная модель ответа (или None).
            params_mapper: функция request_model → params_type (или None).
            response_mapper: функция result_type → response_model (или None).
            tags: теги для OpenAPI (или None).
            summary: краткое описание для OpenAPI.
            description: развёрнутое описание для OpenAPI.
            operation_id: уникальный ID операции (или None).
            deprecated: флаг устаревшего эндпоинта.

        Возвращает:
            Self — текущий экземпляр адаптера для fluent chain.
        """
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
        """
        Регистрирует PATCH-эндпоинт. Возвращает self для fluent chain.

        PATCH используется для частичного обновления ресурса. Параметры
        передаются в JSON body запроса.

        Аргументы:
            path: URL-путь эндпоинта.
            action_class: класс действия (наследник BaseAction[P, R]).
            request_model: протокольная модель запроса (или None).
            response_model: протокольная модель ответа (или None).
            params_mapper: функция request_model → params_type (или None).
            response_mapper: функция result_type → response_model (или None).
            tags: теги для OpenAPI (или None).
            summary: краткое описание для OpenAPI.
            description: развёрнутое описание для OpenAPI.
            operation_id: уникальный ID операции (или None).
            deprecated: флаг устаревшего эндпоинта.

        Возвращает:
            Self — текущий экземпляр адаптера для fluent chain.
        """
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

        Этот метод завершает fluent chain и возвращает готовое приложение.

        Порядок инициализации:
        1. Создание FastAPI-приложения с метаданными OpenAPI.
        2. Добавление middleware для перехвата необработанных исключений.
        3. Регистрация exception handlers для AuthorizationError
           и ValidationFieldError.
        4. Регистрация health check эндпоинта GET /health.
        5. Генерация и регистрация endpoint для каждого маршрута.

        Возвращает:
            FastAPI — готовое приложение с эндпоинтами, middleware,
            exception handlers и health check.
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

        Использует фабрику ``_make_endpoint`` для создания endpoint-функции
        с правильной сигнатурой, затем добавляет маршрут в FastAPI-приложение
        через ``app.add_api_route()``.

        Аргументы:
            app: FastAPI-приложение.
            record: конфигурация маршрута с action_class, моделями,
                    маппингами и OpenAPI-метаданными.
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

        Маппинг:
            AuthorizationError   → HTTP 403 Forbidden
            ValidationFieldError → HTTP 422 Unprocessable Entity

        Общие ошибки (RuntimeError, ValueError и др.) перехватываются
        middleware ``_CatchAllErrorsMiddleware`` и возвращают HTTP 500.

        Аргументы:
            app: FastAPI-приложение, к которому привязываются обработчики.
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
        """
        Добавляет эндпоинт ``GET /health → {"status": "ok"}``.

        Используется для liveness probe в Kubernetes, мониторинга
        и health check балансировщиков нагрузки. Добавляется автоматически
        при вызове build().

        Аргументы:
            app: FastAPI-приложение, к которому добавляется эндпоинт.
        """

        @app.get("/health", tags=["system"])
        async def health_check() -> dict[str, str]:
            return {"status": "ok"}
