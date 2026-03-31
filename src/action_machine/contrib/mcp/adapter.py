# src/action_machine/contrib/mcp/adapter.py
"""
McpAdapter — MCP-адаптер для ActionMachine на базе FastMCP.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

McpAdapter превращает Action в MCP tools для AI-агентов. Один вызов
протокольного метода tool() = один MCP tool. Все протокольные методы
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
4. Создаёт Context (через auth_coordinator или пустой).
5. Получает connections (через connections_factory или None).
6. Создаёт экземпляр Action и вызывает machine.run().
7. Если response_mapper указан — преобразует результат.
8. Возвращает JSON-строку результата.

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
"Action" (например, CreateOrderAction → create_order). Description берётся
из @meta.

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
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.contrib.mcp import McpAdapter

    adapter = McpAdapter(
        machine=machine,
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
from action_machine.auth.auth_coordinator import AuthCoordinator
from action_machine.context.context import Context
from action_machine.core.action_product_machine import ActionProductMachine
from action_machine.core.base_action import BaseAction
from action_machine.core.exceptions import AuthorizationError, ValidationFieldError
from action_machine.resource_managers.base_resource_manager import BaseResourceManager

from .route_record import McpRouteRecord

# ═════════════════════════════════════════════════════════════════════════════
# Вспомогательные функции модульного уровня
# ═════════════════════════════════════════════════════════════════════════════


def _get_meta_description(action_class: type) -> str:
    """
    Извлекает description из ``@meta`` действия.

    Используется для автоматического заполнения description tool,
    если разработчик не указал его явно при регистрации.

    Аргументы:
        action_class: класс действия.

    Возвращает:
        str — description из @meta или пустая строка.
    """
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

    Аргументы:
        name: имя класса в CamelCase.

    Возвращает:
        str — имя в snake_case без суффикса "Action".
    """
    # Удаляем суффикс "Action"
    if name.endswith("Action") and len(name) > len("Action"):
        name = name[: -len("Action")]

    # CamelCase → snake_case
    # Вставляем _ перед каждой заглавной буквой, за которой следует
    # строчная, или перед группой заглавных перед строчной
    result = re.sub(r"(?<=[a-z0-9])([A-Z])", r"_\1", name)
    result = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", result)
    return result.lower()


def _build_graph_json(machine: ActionProductMachine) -> str:
    """
    Строит JSON-представление графа системы из координатора машины.

    Извлекает все узлы и рёбра из rx.PyDiGraph координатора и формирует
    компактное JSON-представление с массивами nodes и edges.

    Формат:
        {
          "nodes": [
            {"id": "...", "type": "action", "description": "...", "domain": "..."},
            {"id": "...", "type": "domain", "name": "..."}
          ],
          "edges": [
            {"from": "...", "to": "...", "type": "belongs_to"}
          ]
        }

    Аргументы:
        machine: машина действий, содержащая координатор с графом.

    Возвращает:
        str — JSON-строка с графом системы.
    """
    graph = machine._coordinator.get_graph()

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    # Собираем узлы
    for idx in graph.node_indices():
        payload = graph[idx]
        node_type = payload.get("node_type", "unknown")
        name = payload.get("name", "")
        meta = payload.get("meta", {})

        node: dict[str, Any] = {
            "id": name,
            "type": node_type,
        }

        # Добавляем description если есть
        description = meta.get("description", "")
        if description:
            node["description"] = description

        # Добавляем domain если есть
        domain = meta.get("domain")
        if domain:
            node["domain"] = domain

        # Для доменных узлов добавляем name из meta
        if node_type == "domain":
            domain_name = meta.get("name", "")
            if domain_name:
                node["name"] = domain_name

        nodes.append(node)

    # Собираем рёбра через weighted_edge_list(), который возвращает
    # кортежи (source_idx, target_idx, edge_data)
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
    auth_coordinator: AuthCoordinator | None,
    connections_factory: Callable[..., dict[str, BaseResourceManager]] | None,
) -> Callable[..., Any]:
    """
    Создаёт async handler для одного MCP tool.

    Handler принимает kwargs от FastMCP (аргументы tool call от агента),
    десериализует их в Pydantic-модель, выполняет действие через machine.run()
    и возвращает JSON-строку результата.

    При ошибке возвращает строку с описанием ошибки — FastMCP доставляет
    её как TextContent агенту.

    Аргументы:
        record: конфигурация маршрута с action_class, моделями и мапперами.
        machine: машина выполнения действий.
        auth_coordinator: координатор аутентификации (или None).
        connections_factory: фабрика соединений (или None).

    Возвращает:
        Async-функцию для передачи в FastMCP через add_tool.
    """
    req_model = record.effective_request_model
    has_params_mapper = record.params_mapper is not None
    has_response_mapper = record.response_mapper is not None

    async def handler(**kwargs: Any) -> str:
        """
        Handler MCP tool call.

        Принимает kwargs от FastMCP, десериализует, выполняет действие,
        возвращает JSON-строку результата или строку ошибки.
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

    # Устанавливаем имя и docstring для FastMCP
    handler.__name__ = record.tool_name.replace(".", "_").replace("-", "_")
    handler.__doc__ = record.description or _get_meta_description(record.action_class)

    return handler


async def _execute_tool_call(
    kwargs: dict[str, Any],
    req_model: type,
    record: McpRouteRecord,
    machine: ActionProductMachine,
    auth_coordinator: AuthCoordinator | None,
    connections_factory: Callable[..., dict[str, BaseResourceManager]] | None,
    has_params_mapper: bool,
    has_response_mapper: bool,
) -> str:
    """
    Выполняет один вызов MCP tool: десериализация, маппинг, выполнение,
    сериализация результата.

    Вынесена из handler для снижения количества return-statements
    и улучшения читаемости.

    Аргументы:
        kwargs: аргументы tool call от агента.
        req_model: Pydantic-модель для десериализации входных данных.
        record: конфигурация маршрута.
        machine: машина выполнения действий.
        auth_coordinator: координатор аутентификации (или None).
        connections_factory: фабрика соединений (или None).
        has_params_mapper: True если указан params_mapper.
        has_response_mapper: True если указан response_mapper.

    Возвращает:
        JSON-строка с результатом выполнения действия.
    """
    # ── 1. Десериализация входных данных ──
    body = req_model.model_validate(kwargs)  # type: ignore[attr-defined]

    # ── 2. Маппинг параметров ──
    params = record.params_mapper(body) if has_params_mapper else body  # type: ignore[misc]

    # ── 3. Аутентификация ──
    context = Context()
    if auth_coordinator is not None:
        auth_context = await auth_coordinator.process(None)
        if auth_context is not None:
            context = auth_context

    # ── 4. Соединения ──
    connections = connections_factory() if connections_factory is not None else None

    # ── 5. Выполнение действия ──
    action = record.action_class()
    result = await machine.run(context, action, params, connections)

    # ── 6. Сериализация результата ──
    return _serialize_result(result, record, has_response_mapper)


def _serialize_result(
    result: Any,
    record: McpRouteRecord,
    has_response_mapper: bool,
) -> str:
    """
    Сериализует результат действия в JSON-строку.

    Если указан response_mapper — применяет его перед сериализацией.

    Аргументы:
        result: результат выполнения действия.
        record: конфигурация маршрута (для доступа к response_mapper).
        has_response_mapper: True если указан response_mapper.

    Возвращает:
        JSON-строка с результатом.
    """
    if has_response_mapper:
        mapped = record.response_mapper(result)  # type: ignore[misc]
        obj = mapped.model_dump() if hasattr(mapped, "model_dump") else mapped
    else:
        obj = result.model_dump() if hasattr(result, "model_dump") else result

    return json.dumps(obj, ensure_ascii=False, default=str)


# ═════════════════════════════════════════════════════════════════════════════
# Класс адаптера
# ═════════════════════════════════════════════════════════════════════════════


class McpAdapter(BaseAdapter[McpRouteRecord]):
    """
    MCP-адаптер для ActionMachine на базе FastMCP.

    Наследует BaseAdapter[McpRouteRecord]. Предоставляет протокольный
    метод tool() для регистрации MCP tools. Метод build() завершает
    fluent chain и создаёт FastMCP-сервер.

    Метод register_all() автоматически регистрирует все Action из
    координатора машины, формируя имена tools в snake_case.

    При build() дополнительно регистрируется MCP resource ``system://graph``,
    возвращающий JSON с графом системы.

    Атрибуты:
        _server_name : str
            Имя MCP-сервера. Отображается при подключении клиента.

        _server_version : str
            Версия MCP-сервера.
    """

    def __init__(
        self,
        machine: ActionProductMachine,
        auth_coordinator: AuthCoordinator | None = None,
        connections_factory: Callable[..., dict[str, BaseResourceManager]] | None = None,
        server_name: str = "ActionMachine MCP",
        server_version: str = "0.1.0",
    ) -> None:
        """
        Инициализирует MCP-адаптер.

        Аргументы:
            machine: машина выполнения действий. Обязательный параметр.
                     Должен быть экземпляром ActionProductMachine.
            auth_coordinator: координатор аутентификации. Если указан,
                              вызывается для каждого tool call. Если None —
                              Context создаётся пустым.
            connections_factory: фабрика соединений. Если указана, вызывается
                                 перед каждым machine.run(). Если None —
                                 connections не передаются.
            server_name: имя MCP-сервера. Отображается при подключении
                         клиента (Claude Desktop, MCP Inspector и др.).
                         По умолчанию "ActionMachine MCP".
            server_version: версия MCP-сервера. По умолчанию "0.1.0".
        """
        super().__init__(
            machine=machine,
            auth_coordinator=auth_coordinator,
            connections_factory=connections_factory,
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
    # Протокольный метод регистрации (fluent — возвращает Self)
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
        Регистрирует MCP tool. Возвращает self для fluent chain.

        Один вызов tool() = один MCP tool, видимый AI-агенту. inputSchema
        генерируется автоматически из effective_request_model.model_json_schema().

        Если description пуст — подставляется description из ``@meta`` действия.

        Аргументы:
            name: имя MCP tool, видимое агенту. Непустая строка.
                  Рекомендуемый формат: ``domain.action`` — например,
                  ``orders.create``, ``system.ping``.
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
                           None если request_model совпадает с params_type.
            response_mapper: функция преобразования result_type → response_model.
                             None если response_model совпадает с result_type.
            description: описание tool для AI-агента. Пустая строка —
                         адаптер подставит description из ``@meta`` действия.

        Возвращает:
            Self — текущий экземпляр адаптера для fluent chain.
        """
        effective_description = description or _get_meta_description(action_class)

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

        Обходит все классы, зарегистрированные в координаторе машины.
        Для каждого класса, содержащего аспекты (т.е. являющегося Action),
        создаёт MCP tool с:

        - tool_name: snake_case от имени класса без суффикса "Action".
          Например: CreateOrderAction → create_order.
        - description: из @meta действия.
        - inputSchema: из model_json_schema() модели Params.

        Возвращает:
            Self — текущий экземпляр адаптера для fluent chain.

        Пример:
            adapter.register_all().build()
        """
        coordinator = self._machine._coordinator

        for cls in coordinator.get_all_classes():
            metadata = coordinator.get(cls)

            # Регистрируем только Action (классы с аспектами)
            if not metadata.has_aspects():
                continue

            tool_name = _class_name_to_snake_case(cls.__name__)
            description = metadata.meta.description if metadata.meta else ""

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

        Этот метод завершает fluent chain и возвращает готовый MCP-сервер.

        Порядок инициализации:
        1. Создание FastMCP-сервера с именем и версией.
        2. Для каждого маршрута: создание handler и регистрация tool
           на сервере с inputSchema из model_json_schema().
        3. Регистрация resource ``system://graph``.

        Возвращает:
            FastMCP — готовый MCP-сервер с зарегистрированными tools
            и resource system://graph.
        """
        mcp = FastMCP(self._server_name)

        # ── Регистрация tools ──
        for record in self._routes:
            self._register_tool(mcp, record)

        # ── Регистрация resource system://graph ──
        self._register_graph_resource(mcp)

        return mcp

    # ─────────────────────────────────────────────────────────────────────
    # Регистрация одного tool на FastMCP-сервере
    # ─────────────────────────────────────────────────────────────────────

    def _register_tool(self, mcp: FastMCP, record: McpRouteRecord) -> None:
        """
        Создаёт и регистрирует один MCP tool на FastMCP-сервере.

        Генерирует async handler через _make_tool_handler и регистрирует
        его как tool на FastMCP-сервере через mcp.add_tool().

        inputSchema берётся из effective_request_model.model_json_schema().
        FastMCP использует его для валидации входных данных от агента
        и для отображения схемы параметров.

        Аргументы:
            mcp: FastMCP-сервер, на котором регистрируется tool.
            record: конфигурация маршрута с action_class, моделями,
                    мапперами и MCP-метаданными.
        """
        handler = _make_tool_handler(
            record=record,
            machine=self._machine,
            auth_coordinator=self._auth_coordinator,
            connections_factory=self._connections_factory,
        )

        # Регистрируем tool на FastMCP-сервере.
        # FastMCP автоматически генерирует inputSchema из сигнатуры handler,
        # но мы используем декоратор с явным именем и описанием.
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

        Resource возвращает JSON с узлами и рёбрами графа координатора.
        AI-агент может запросить этот ресурс, чтобы увидеть структуру
        системы: какие действия существуют, к каким доменам принадлежат,
        от чего зависят.

        Аргументы:
            mcp: FastMCP-сервер, на котором регистрируется resource.
        """
        machine = self._machine

        @mcp.resource("system://graph")
        def get_system_graph() -> str:
            """
            Структура системы ActionMachine.

            Возвращает JSON с узлами (actions, domains, dependencies,
            resource managers) и рёбрами (depends, belongs_to, connection)
            графа координатора. Позволяет AI-агенту исследовать
            архитектуру системы.
            """
            return _build_graph_json(machine)
