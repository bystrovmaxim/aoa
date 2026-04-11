# src/action_machine/contrib/mcp/adapter.py
"""
McpAdapter — MCP-адаптер для ActionMachine на базе FastMCP.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

McpAdapter превращает Action в MCP tools для AI-агентов. Один вызов
протокольного methodа tool() = один MCP tool. Все протокольные methodы
возвращают self для поддержки fluent chain:

    server = adapter \\
        .tool("system.ping", PingAction) \\
        .tool("orders.create", CreateOrderAction) \\
        .build()

inputSchema генерируется автоматически из Pydantic-модели Params через
model_json_schema(). Описания полей из Field(description=...),
constraints из Field(gt=0, min_length=3), examples — всё попадает
в inputSchema без дублирования.

═══════════════════════════════════════════════════════════════════════════════
ОБЯЗАТЕЛЬНАЯ АУТЕНТИФИКАЦИЯ
═══════════════════════════════════════════════════════════════════════════════

Параметр auth_coordinator обязателен (наследуется от BaseAdapter).
Для открытых API используется NoAuthCoordinator — явная декларация
отсутствия аутентификации:

    adapter = McpAdapter(
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
СТРАТЕГИЯ ГЕНЕРАЦИИ TOOL HANDLER
═══════════════════════════════════════════════════════════════════════════════

Для каждого зарегистрированного McpRouteRecord адаптер создаёт
async handler-функцию, которая:

1. Получает аргументы tool call как kwargs от FastMCP.
2. Десериализует их в effective_request_model через model_validate().
3. Если params_mapper указан — преобразует в params_type.
4. Создаёт Context (через auth_coordinator).
5. Получает connections (через connections_factory или None).
6. Создаёт экземпляр Action и вызывает machine.run().
7. Если response_mapper указан — преобразует результат.
8. Returns JSON-строку result.

При ошибке handler возвращает строку с описанием ошибки и пометкой
типа ошибки (PERMISSION_DENIED, INVALID_PARAMS, INTERNAL_ERROR).
FastMCP доставляет это как TextContent с isError=True.

═══════════════════════════════════════════════════════════════════════════════
RESOURCE system://graph
═══════════════════════════════════════════════════════════════════════════════

При build() адаптер регистрирует MCP resource ``system://graph``.
Resource возвращает JSON с узлами и рёбрами графа координатора:

    {
      "nodes": [
        {"id": "...", "type": "action", "description": "...", "domain": "..."},
        {"id": "...", "type": "domain", "name": "..."}
      ],
      "edges": [
        {"from": "...", "to": "...", "type": "belongs_to"}
      ]
    }

Это позволяет AI-агенту исследовать архитектуру системы: какие действия
существуют, к каким доменам принадлежат, от чего зависят.

═══════════════════════════════════════════════════════════════════════════════
МЕТОД register_all()
═══════════════════════════════════════════════════════════════════════════════

Автоматически регистрирует все Action из координатора машины как MCP tools.
        Имя tool формируется из имени класса в snake_case с удалением суффикса
"Action" (например, CreateOrderAction → create_order). Classы действий
находятся через ``get_nodes_by_type("aspect")``; description — из
``get_snapshot(cls, "meta")`` (fallback: scratch ``_meta_info``).

═══════════════════════════════════════════════════════════════════════════════
ОБРАБОТКА ОШИБОК
═══════════════════════════════════════════════════════════════════════════════

Ошибки не подавляются — они преобразуются в текстовый ответ с пометкой:

    AuthorizationError      → "PERMISSION_DENIED: ..."
    ValidationFieldError    → "INVALID_PARAMS: ..."
    Exception               → "INTERNAL_ERROR: ..."

FastMCP возвращает их как TextContent, что позволяет AI-агенту прочитать
сообщение об ошибке и скорректировать следующий запрос.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.auth.no_auth_coordinator import NoAuthCoordinator
    from action_machine.contrib.mcp import McpAdapter

    adapter = McpAdapter(
        machine=machine,
        auth_coordinator=NoAuthCoordinator(),
        server_name="Orders MCP",
        server_version="0.1.0",
    )

    server = adapter \\
        .tool("orders.create", CreateOrderAction) \\
        .tool("orders.get", GetOrderAction) \\
        .tool("system.ping", PingAction) \\
        .build()

    server.run(transport="stdio")
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import Any, Self

from mcp.server.fastmcp import FastMCP

from action_machine.adapters.base_adapter import BaseAdapter
from action_machine.context.context import Context
from action_machine.core.action_product_machine import ActionProductMachine
from action_machine.core.base_action import BaseAction
from action_machine.core.exceptions import AuthorizationError, ValidationFieldError
from action_machine.metadata.gate_coordinator import GateCoordinator
from action_machine.resource_managers.base_resource_manager import BaseResourceManager

from .route_record import McpRouteRecord

# ═════════════════════════════════════════════════════════════════════════════
# Вспомогательные функции модульного уровня
# ═════════════════════════════════════════════════════════════════════════════


def _get_meta_description(
    action_class: type,
    *,
    coordinator: GateCoordinator | None = None,
) -> str:
    """
    Извлекает description для MCP tool из метаданных действия.

    Предпочитает снимок facet ``meta`` построенного координатора
    (``get_snapshot(action_class, "meta")``); если снимка нет —
    читает scratch ``_meta_info`` с класса (как у runtime).

    Args:
        action_class: класс действия.
        coordinator: координатор машины (если есть и построен).

    Returns:
        str — description или пустая строка.
    """
    if coordinator is not None and coordinator.is_built:
        meta_snap = coordinator.get_snapshot(action_class, "meta")
        if meta_snap is not None:
            return str(getattr(meta_snap, "description", "") or "")
    meta_info = getattr(action_class, "_meta_info", None)
    if meta_info and isinstance(meta_info, dict):
        return str(meta_info.get("description", ""))
    return ""


def _class_name_to_snake_case(name: str) -> str:
    """
    Преобразует CamelCase имя класса в snake_case.

    Удаляет суффикс "Action" перед преобразованием.
    Например: CreateOrderAction → create_order,
              GetOrderAction → get_order,
              PingAction → ping.

    Args:
        name: имя класса в CamelCase.

    Returns:
        str — имя в snake_case без суффикса "Action".
    """
    if name.endswith("Action") and len(name) > len("Action"):
        name = name[: -len("Action")]

    result = re.sub(r"(?<=[a-z0-9])([A-Z])", r"_\1", name)
    result = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", result)
    return result.lower()


def _build_graph_json(coordinator: GateCoordinator) -> str:
    """
    Строит JSON-представление графа системы из координатора.

    Извлекает все узлы и рёбра из rx.PyDiGraph координатора и формирует
    компактное JSON-представление с массивами nodes и edges.

    Args:
        coordinator: построенный ``GateCoordinator`` с графом.

    Returns:
        str — JSON-строка с графом системы.
    """
    graph = coordinator.get_graph()

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    for idx in graph.node_indices():
        payload = graph[idx]
        node_type = payload.get("node_type", "unknown")
        name = payload.get("name", "")
        meta = payload.get("meta", {})

        node: dict[str, Any] = {
            "id": name,
            "type": node_type,
        }

        description = meta.get("description", "")
        if description:
            node["description"] = description

        # В payload узла ``meta`` поле ``domain`` — это обычно *класс* BaseDomain.
        # ``json.dumps`` не сериализует ``type`` (error «ABCMeta is not JSON serializable»).
        # Для MCP resource отдаём стабильную строку ``module.QualName``; для нестандартных
        # значений — ``str(domain)``, чтобы агент всё равно получил читаемый текст.
        domain = meta.get("domain")
        if domain:
            if isinstance(domain, type):
                node["domain"] = f"{domain.__module__}.{domain.__qualname__}"
            else:
                node["domain"] = str(domain)

        if node_type == "domain":
            domain_name = meta.get("name", "")
            if domain_name:
                node["name"] = domain_name

        nodes.append(node)

    for source, target, edge_data in graph.weighted_edge_list():
        source_payload = graph[source]
        target_payload = graph[target]

        edge_type = edge_data if isinstance(edge_data, str) else str(edge_data)

        edges.append({
            "from": source_payload.get("name", ""),
            "to": target_payload.get("name", ""),
            "type": edge_type,
        })

    result = {
        "nodes": nodes,
        "edges": edges,
    }

    return json.dumps(result, ensure_ascii=False, indent=2)


# ═════════════════════════════════════════════════════════════════════════════
# Фабрика handler-функций для MCP tools
# ═════════════════════════════════════════════════════════════════════════════


def _make_tool_handler(
    record: McpRouteRecord,
    machine: ActionProductMachine,
    auth_coordinator: Any,
    connections_factory: Callable[..., dict[str, BaseResourceManager]] | None,
    gate_coordinator: GateCoordinator,
) -> Callable[..., Any]:
    """
    Создаёт async handler для одного MCP tool.

    Handler принимает kwargs от FastMCP (аргументы tool call от агента),
    десериализует их в Pydantic-модель, выполняет действие через machine.run()
    и возвращает JSON-строку result.

    При ошибке возвращает строку с описанием ошибки — FastMCP доставляет
    её как TextContent агенту.

    Args:
        record: конфигурация маршрута с action_class, моделями и мапперами.
        machine: машина выполнения действий.
        auth_coordinator: координатор аутентификации (AuthCoordinator
                          или NoAuthCoordinator).
        connections_factory: фабрика соединений (или None).
        gate_coordinator: координатор для метаданных tool (описание из facet).

    Returns:
        Async-функцию для передачи в FastMCP через add_tool.
    """
    req_model = record.effective_request_model
    has_params_mapper = record.params_mapper is not None
    has_response_mapper = record.response_mapper is not None

    async def handler(**kwargs: Any) -> str:
        """
        Handler MCP tool call.

        Принимает kwargs от FastMCP, десериализует, выполняет действие,
        возвращает JSON-строку result или строку ошибки.
        """
        try:
            return await _execute_tool_call(
                kwargs, req_model, record, machine,
                auth_coordinator, connections_factory,
                has_params_mapper, has_response_mapper,
            )
        except AuthorizationError as exc:
            return f"PERMISSION_DENIED: {exc}"
        except ValidationFieldError as exc:
            return f"INVALID_PARAMS: {exc}"
        except Exception as exc:
            return f"INTERNAL_ERROR: {exc}"

    handler.__name__ = record.tool_name.replace(".", "_").replace("-", "_")
    handler.__doc__ = record.description or _get_meta_description(
        record.action_class,
        coordinator=gate_coordinator,
    )

    return handler


async def _execute_tool_call(
    kwargs: dict[str, Any],
    req_model: type,
    record: McpRouteRecord,
    machine: ActionProductMachine,
    auth_coordinator: Any,
    connections_factory: Callable[..., dict[str, BaseResourceManager]] | None,
    has_params_mapper: bool,
    has_response_mapper: bool,
) -> str:
    """
    Выполняет один вызов MCP tool: десериализация, маппинг, выполнение,
    сериализация result.

    Args:
        kwargs: аргументы tool call от агента.
        req_model: Pydantic-модель для десериализации входных данных.
        record: конфигурация маршрута.
        machine: машина выполнения действий.
        auth_coordinator: координатор аутентификации.
        connections_factory: фабрика соединений (или None).
        has_params_mapper: True если указан params_mapper.
        has_response_mapper: True если указан response_mapper.

    Returns:
        JSON-строка с результатом выполнения действия.
    """
    body = req_model.model_validate(kwargs)  # type: ignore[attr-defined]

    params = record.params_mapper(body) if has_params_mapper else body  # type: ignore[misc]

    context = await auth_coordinator.process(None)
    if context is None:
        context = Context()

    connections = connections_factory() if connections_factory is not None else None

    action = record.action_class()
    result = await machine.run(context, action, params, connections)

    return _serialize_result(result, record, has_response_mapper)


def _serialize_result(
    result: Any,
    record: McpRouteRecord,
    has_response_mapper: bool,
) -> str:
    """
    Сериализует результат действия в JSON-строку.

    Если указан response_mapper — применяет его перед сериализацией.

    Args:
        result: результат выполнения действия.
        record: конфигурация маршрута (для доступа к response_mapper).
        has_response_mapper: True если указан response_mapper.

    Returns:
        JSON-строка с результатом.
    """
    if has_response_mapper:
        mapped = record.response_mapper(result)  # type: ignore[misc]
        obj = mapped.model_dump() if hasattr(mapped, "model_dump") else mapped
    else:
        obj = result.model_dump() if hasattr(result, "model_dump") else result

    return json.dumps(obj, ensure_ascii=False, default=str)


# ═════════════════════════════════════════════════════════════════════════════
# Class адаптера
# ═════════════════════════════════════════════════════════════════════════════


class McpAdapter(BaseAdapter[McpRouteRecord]):
    """
    MCP-адаптер для ActionMachine на базе FastMCP.

    Наследует BaseAdapter[McpRouteRecord]. Предоставляет протокольный
    method tool() для регистрации MCP tools. Метод build() завершает
    fluent chain и создаёт FastMCP-сервер.

    Метод register_all() автоматически регистрирует все Action из
    координатора машины, формируя имена tools в snake_case.

    При build() дополнительно регистрируется MCP resource ``system://graph``,
    возвращающий JSON с графом системы.

    Параметр auth_coordinator обязателен (наследуется от BaseAdapter).
    Для открытых API используется NoAuthCoordinator().

    Атрибуты:
        _server_name : str
            Имя MCP-сервера. Отображается при подключении клиента.

        _server_version : str
            Версия MCP-сервера.
    """

    def __init__(
        self,
        machine: ActionProductMachine,
        auth_coordinator: Any,
        connections_factory: Callable[..., dict[str, BaseResourceManager]] | None = None,
        *,
        gate_coordinator: GateCoordinator | None = None,
        server_name: str = "ActionMachine MCP",
        server_version: str = "0.1.0",
    ) -> None:
        """
        Инициализирует MCP-адаптер.

        Args:
            machine: машина выполнения действий. Обязательный параметр.
                     Должен быть экземпляром ActionProductMachine.
            auth_coordinator: координатор аутентификации. Обязательный параметр.
                              Для открытых API используйте NoAuthCoordinator().
                              None не допускается — TypeError.
            connections_factory: фабрика соединений. Если указана, вызывается
                                 перед каждым machine.run(). Если None —
                                 connections не передаются.
            gate_coordinator: явный ``GateCoordinator`` для графа и снапшотов;
                              по умолчанию ``machine.gate_coordinator``.
            server_name: имя MCP-сервера. Отображается при подключении
                         клиента (Claude Desktop, MCP Inspector и др.).
                         По умолчанию "ActionMachine MCP".
            server_version: версия MCP-сервера. По умолчанию "0.1.0".
        """
        super().__init__(
            machine=machine,
            auth_coordinator=auth_coordinator,
            connections_factory=connections_factory,
            gate_coordinator=gate_coordinator,
        )
        self._server_name: str = server_name
        self._server_version: str = server_version

    # ─────────────────────────────────────────────────────────────────────
    # Свойства
    # ─────────────────────────────────────────────────────────────────────

    @property
    def server_name(self) -> str:
        """Имя MCP-сервера."""
        return self._server_name

    @property
    def server_version(self) -> str:
        """Версия MCP-сервера."""
        return self._server_version

    # ─────────────────────────────────────────────────────────────────────
    # Протокольный method регистрации (fluent — возвращает Self)
    # ─────────────────────────────────────────────────────────────────────

    def tool(
        self,
        name: str,
        action_class: type[BaseAction[Any, Any]],
        request_model: type | None = None,
        response_model: type | None = None,
        params_mapper: Callable[..., Any] | None = None,
        response_mapper: Callable[..., Any] | None = None,
        description: str = "",
    ) -> Self:
        """
        Регистрирует MCP tool. Returns self для fluent chain.

        Один вызов tool() = один MCP tool, видимый AI-агенту. inputSchema
        генерируется автоматически из effective_request_model.model_json_schema().

        Если description пуст — подставляется description из ``@meta`` действия.

        Args:
            name: имя MCP tool, видимое агенту. Непустая строка.
                  Рекомендуемый формат: ``domain.action`` — например,
                  ``orders.create``, ``system.ping``.
            action_class: класс действия (наследник BaseAction[P, R]).
            request_model: протокольная модель входящего запроса. Если None —
                           используется params_type.
            response_model: протокольная модель ответа. Если None —
                            используется result_type.
            params_mapper: функция преобразования request_model → params_type.
            response_mapper: функция преобразования result_type → response_model.
            description: описание tool для AI-агента. Пустая строка —
                         адаптер подставит description из ``@meta`` действия.

        Returns:
            Self — текущий экземпляр адаптера для fluent chain.
        """
        effective_description = description or _get_meta_description(
            action_class,
            coordinator=self.gate_coordinator,
        )

        record = McpRouteRecord(
            action_class=action_class,
            request_model=request_model,
            response_model=response_model,
            params_mapper=params_mapper,
            response_mapper=response_mapper,
            tool_name=name,
            description=effective_description,
        )
        return self._add_route(record)

    # ─────────────────────────────────────────────────────────────────────
    # Автоматическая регистрация всех Action
    # ─────────────────────────────────────────────────────────────────────

    def register_all(self) -> Self:
        """
        Автоматически регистрирует все Action из координатора как MCP tools.

        Обходит узлы графа координатора с типом ``aspect``, для каждого
        класса-действия с непустым снимком ``get_snapshot(cls, "aspect")``
        создаёт MCP tool с:

        - tool_name: snake_case от имени класса без суффикса "Action".
        - description: из ``get_snapshot(cls, "meta")`` (иначе scratch ``_meta_info``).
        - inputSchema: из model_json_schema() модели Params.

        Returns:
            Self — текущий экземпляр адаптера для fluent chain.
        """
        coordinator = self.gate_coordinator

        action_nodes = coordinator.get_nodes_by_type("aspect")
        seen: set[type] = set()
        for node in action_nodes:
            cls = node.get("class_ref")
            if not isinstance(cls, type):
                continue
            if cls in seen or not issubclass(cls, BaseAction):
                continue
            seen.add(cls)

            aspect_snap = coordinator.get_snapshot(cls, "aspect")
            aspects = getattr(aspect_snap, "aspects", ()) if aspect_snap is not None else ()
            if not aspects:
                continue

            tool_name = _class_name_to_snake_case(cls.__name__)
            m = coordinator.get_snapshot(cls, "meta")
            description = m.description if m is not None and hasattr(m, "description") else ""

            self.tool(
                name=tool_name,
                action_class=cls,
                description=description,
            )

        return self

    # ─────────────────────────────────────────────────────────────────────
    # Построение FastMCP-сервера
    # ─────────────────────────────────────────────────────────────────────

    def build(self) -> FastMCP:
        """
        Создаёт FastMCP-сервер из зарегистрированных маршрутов.

        Порядок инициализации:
        1. Создание FastMCP-сервера с именем и версией.
        2. Для каждого маршрута: создание handler и регистрация tool.
        3. Регистрация resource ``system://graph``.

        Returns:
            FastMCP — готовый MCP-сервер с зарегистрированными tools
            и resource system://graph.
        """
        mcp = FastMCP(self._server_name)

        for record in self._routes:
            self._register_tool(mcp, record)

        self._register_graph_resource(mcp)

        return mcp

    # ─────────────────────────────────────────────────────────────────────
    # Регистрация одного tool на FastMCP-сервере
    # ─────────────────────────────────────────────────────────────────────

    def _register_tool(self, mcp: FastMCP, record: McpRouteRecord) -> None:
        """
        Создаёт и регистрирует один MCP tool на FastMCP-сервере.

        Args:
            mcp: FastMCP-сервер, на котором регистрируется tool.
            record: конфигурация маршрута.
        """
        handler = _make_tool_handler(
            record=record,
            machine=self._machine,
            auth_coordinator=self._auth_coordinator,
            connections_factory=self._connections_factory,
            gate_coordinator=self.gate_coordinator,
        )

        mcp.add_tool(
            handler,
            name=record.tool_name,
            description=record.description,
        )

    # ─────────────────────────────────────────────────────────────────────
    # Регистрация resource system://graph
    # ─────────────────────────────────────────────────────────────────────

    def _register_graph_resource(self, mcp: FastMCP) -> None:
        """
        Регистрирует MCP resource ``system://graph`` на FastMCP-сервере.

        AI-агент может запросить этот ресурс, чтобы увидеть структуру
        системы: какие действия существуют, к каким доменам принадлежат,
        от чего зависят.

        Args:
            mcp: FastMCP-сервер, на котором регистрируется resource.
        """
        coordinator = self.gate_coordinator

        @mcp.resource("system://graph")
        def get_system_graph() -> str:
            """
            Структура системы ActionMachine.

            Returns JSON с узлами (actions, domains, dependencies,
            resource managers) и рёбрами (depends, belongs_to, connection)
            графа координатора.
            """
            return _build_graph_json(coordinator)
