# src/action_machine/core/gate_coordinator.py
"""
GateCoordinator — центральный реестр метаданных, фабрик зависимостей
и направленного ациклического графа всех сущностей системы.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

GateCoordinator — единственная точка доступа к метаданным классов, фабрикам
зависимостей и структурному графу во всей системе ActionMachine. Он отвечает за:

1. ЛЕНИВУЮ СБОРКУ МЕТАДАННЫХ: при первом обращении к классу координатор
   вызывает MetadataBuilder.build(cls), получает ClassMetadata и кеширует его.
   Повторные обращения возвращают кешированный объект мгновенно.

2. КЕШИРОВАНИЕ МЕТАДАННЫХ: каждый класс собирается ровно один раз. Кеш
   привязан к самому объекту класса (type).

3. ВЛАДЕНИЕ ФАБРИКАМИ ЗАВИСИМОСТЕЙ: координатор создаёт DependencyFactory
   напрямую из metadata.dependencies. Фабрика stateless, один экземпляр
   безопасно разделяется между всеми вызовами run().

4. РЕКУРСИВНЫЙ ОБХОД ЗАВИСИМОСТЕЙ: после сборки ClassMetadata координатор
   проходит по metadata.dependencies и metadata.connections, рекурсивно
   вызывая get() для каждого найденного класса.

5. ПОСТРОЕНИЕ И КОНТРОЛЬ ГРАФА: координатор создаёт направленный граф
   rx.PyDiGraph при инициализации. При регистрации каждого класса граф
   заполняется узлами и рёбрами. Ацикличность проверяется для структурных
   рёбер (depends, connection) через _add_edge_checked. Leaf-рёбра
   (has_aspect, has_checker, has_role, has_sensitive, subscribes,
   belongs_to, has_error_handler, requires_context) добавляются напрямую
   без проверки ацикличности — они ведут к leaf-узлам, не имеющим
   исходящих рёбер, и цикл невозможен по конструкции.

6. STRICT-РЕЖИМ: если strict=True, координатор проверяет, что domain указан
   в @meta для Action и ResourceManager.

7. ДОМЕННЫЕ УЗЛЫ: если @meta указывает domain, координатор создаёт узел
   типа "domain" и ребро "belongs_to" от класса к домену.

8. УЗЛЫ ОБРАБОТЧИКОВ ОШИБОК: каждый @on_error обработчик представлен
   узлом типа "error_handler" с атрибутами exception_types, method_name,
   description. Ребро "has_error_handler" от action к error_handler.

9. УЗЛЫ КОНТЕКСТНЫХ ЗАВИСИМОСТЕЙ: для каждого аспекта или обработчика
   ошибок с @context_requires создаются рёбра "requires_context" от узла
   аспекта/обработчика к узлам типа "context_field". Узлы context_field
   переиспользуются: если два аспекта запрашивают user.user_id, создаётся
   один узел и два ребра к нему.

═══════════════════════════════════════════════════════════════════════════════
ГРАФ СУЩНОСТЕЙ
═══════════════════════════════════════════════════════════════════════════════

Граф строится на библиотеке rustworkx (rx.PyDiGraph) и содержит все сущности
системы: действия, зависимости, соединения, плагины, аспекты, чекеры,
обработчики ошибок, подписки, чувствительные поля, роли, домены и поля
контекста.

Типы узлов:
    action, dependency, connection, plugin, aspect, checker,
    error_handler, subscription, sensitive, role, domain, context_field.

Типы рёбер:
    depends, connection — структурные, проверяются на ацикличность.
    has_aspect, has_checker, has_error_handler, has_sensitive, has_role,
    subscribes, belongs_to, requires_context — leaf-рёбра, добавляются
    напрямую без проверки.

═══════════════════════════════════════════════════════════════════════════════
ФОРМАТ КЛЮЧЕЙ УЗЛОВ
═══════════════════════════════════════════════════════════════════════════════

Каждый узел идентифицируется строковым ключом формата ``"тип:полное_имя"``.
Ключ используется в публичных методах get_node(), get_children(),
get_dependency_tree():

    "action:module.path.CreateOrderAction"
    "dependency:module.path.PaymentService"
    "connection:module.path.PostgresManager"
    "domain:orders"
    "aspect:module.path.CreateOrderAction.validate_aspect"
    "checker:module.path.CreateOrderAction.validate_aspect.txn_id"
    "error_handler:module.path.CreateOrderAction.validation_on_error"
    "context_field:user.user_id"
    "context_field:request.trace_id"
    "role:module.path.CreateOrderAction.role"
    "sensitive:module.path.UserAccount.email"
    "subscription:module.path.MetricsPlugin.subscription_0_global_finish"
    "plugin:module.path.MetricsPlugin"

Примеры использования:

    coordinator.get_node("action:module.CreateOrderAction")
    coordinator.get_node("context_field:user.user_id")
    coordinator.get_children("domain:orders")
    coordinator.get_nodes_by_type("context_field")

═══════════════════════════════════════════════════════════════════════════════
КОНТЕКСТНЫЕ ЗАВИСИМОСТИ В ГРАФЕ
═══════════════════════════════════════════════════════════════════════════════

Декоратор @context_requires записывает frozenset ключей (dot-path) в
AspectMeta.context_keys и OnErrorMeta.context_keys. При заполнении графа
координатор создаёт:

- Узел "context_field" для каждого уникального dot-path (например,
  "user.user_id", "request.trace_id"). Узлы переиспользуются через
  _ensure_node — идемпотентно.

- Ребро "requires_context" от узла аспекта (или обработчика ошибок)
  к узлу context_field.

Рёбра requires_context — leaf-рёбра. Узлы context_field не имеют
исходящих рёбер, поэтому цикл невозможен по конструкции. Проверка
ацикличности не выполняется — используется прямой graph.add_edge().

Это позволяет:
- Визуализировать, какие аспекты обращаются к каким полям контекста.
- Строить отчёты: coordinator.get_nodes_by_type("context_field").
- AI-агенту через MCP resource system://graph видеть зависимости.
- Обнаруживать чрезмерные зависимости от контекста.

═══════════════════════════════════════════════════════════════════════════════
АРХИТЕКТУРА
═══════════════════════════════════════════════════════════════════════════════

    ┌───────────────────────┐
    │  ActionProductMachine  │
    │  PluginCoordinator     │        потребители
    └──────────┬────────────┘
               │
               │  coordinator.get(cls)          → ClassMetadata
               │  coordinator.get_factory(cls)  → DependencyFactory
               │  coordinator.get_graph()       → rx.PyDiGraph (копия)
               ▼
    ┌──────────────────────────┐
    │  GateCoordinator          │
    │                          │
    │  _cache: dict[type, CM]  │──── cls → ClassMetadata
    │  _factory_cache: dict    │──── cls → DependencyFactory
    │  _graph: rx.PyDiGraph    │──── направленный граф сущностей
    │  _node_index: dict       │──── ключ узла → индекс в графе
    │  _strict: bool           │──── strict-режим проверки domain
    │                          │
    └──────────┬───────────────┘
               │  cache miss → MetadataBuilder.build(cls)
               ▼
    ┌──────────────────┐
    │  MetadataBuilder  │
    └──────────────────┘
"""

from __future__ import annotations

from typing import Any

import rustworkx as rx  # pylint: disable=no-member

from action_machine.core.class_metadata import ClassMetadata, MetaInfo, RoleMeta
from action_machine.core.exceptions import CyclicDependencyError
from action_machine.core.meta_gate_hosts import ActionMetaGateHost, ResourceMetaGateHost
from action_machine.dependencies.dependency_factory import DependencyFactory
from action_machine.metadata import MetadataBuilder


def _full_class_name(cls: type) -> str:
    """
    Формирует полное имя класса: module.ClassName.

    Если модуль ``__main__`` или отсутствует, возвращает просто имя класса.
    """
    module = getattr(cls, "__module__", None)
    if module and module != "__main__":
        return f"{module}.{cls.__qualname__}"
    return cls.__qualname__


class GateCoordinator:
    """
    Центральный реестр метаданных, фабрик зависимостей и графа сущностей.

    Хранит собранные метаданные классов, stateless-фабрики зависимостей
    и направленный ациклический граф всех сущностей системы. Предоставляет
    доступ через get(), get_factory() и методы чтения графа.

    При первом обращении к классу автоматически вызывает MetadataBuilder.build(),
    кеширует результат, рекурсивно обходит зависимости и соединения,
    заполняет граф узлами и рёбрами.

    Структурные рёбра (depends, connection) проверяются на ацикличность.
    Leaf-рёбра (has_aspect, has_checker, requires_context и др.) добавляются
    напрямую — цикл невозможен по конструкции.

    В strict-режиме дополнительно проверяет обязательность domain в @meta.

    Атрибуты:
        _cache : dict[type, ClassMetadata]
            Кеш метаданных. Ключ — сам объект класса (type).
        _factory_cache : dict[type, DependencyFactory]
            Кеш stateless-фабрик зависимостей.
        _graph : rx.PyDiGraph
            Направленный граф сущностей системы.
        _node_index : dict[str, int]
            Карта ключ_узла → индекс_в_графе.
            Формат ключа: ``"тип:полное_имя"`` (например,
            ``"action:module.CreateOrderAction"``,
            ``"context_field:user.user_id"``).
        _strict : bool
            Если True — domain обязателен в @meta для Action и ResourceManager.
    """

    def __init__(self, strict: bool = False) -> None:
        """
        Создаёт координатор с пустым графом.

        Аргументы:
            strict: если True, при get(cls) проверяется обязательность
                    domain в @meta для Action и ResourceManager.
        """
        self._cache: dict[type, ClassMetadata] = {}
        self._factory_cache: dict[type, DependencyFactory] = {}
        self._graph = rx.PyDiGraph()  # pylint: disable=no-member
        self._node_index: dict[str, int] = {}
        self._strict: bool = strict

    @property
    def strict(self) -> bool:
        """Возвращает текущий strict-режим координатора."""
        return self._strict

    # ─────────────────────────────────────────────────────────────────────
    # Внутренние методы: strict-валидация
    # ─────────────────────────────────────────────────────────────────────

    def _validate_strict_domain(self, cls: type, metadata: ClassMetadata) -> None:
        """В strict-режиме проверяет обязательность domain в @meta."""
        if not self._strict:
            return

        if metadata.meta is None:
            return

        if metadata.meta.domain is not None:
            return

        if issubclass(cls, ActionMetaGateHost) and metadata.has_aspects():
            raise ValueError(
                f"strict режим: Action {cls.__name__} не привязан к домену. "
                f"Укажите domain в @meta, например: "
                f'@meta(description="...", domain=MyDomain).'
            )

        if issubclass(cls, ResourceMetaGateHost):
            raise ValueError(
                f"strict режим: ресурсный менеджер {cls.__name__} не привязан "
                f"к домену. Укажите domain в @meta, например: "
                f'@meta(description="...", domain=MyDomain).'
            )

    # ─────────────────────────────────────────────────────────────────────
    # Внутренние методы: работа с графом
    # ─────────────────────────────────────────────────────────────────────

    def _make_node_key(self, node_type: str, name: str) -> str:
        """
        Формирует уникальный ключ узла: ``"тип:полное_имя"``.

        Этот же формат используется в публичных методах get_node(),
        get_children(), get_dependency_tree().

        Примеры:
            ``"action:module.CreateOrderAction"``
            ``"context_field:user.user_id"``
            ``"domain:orders"``
        """
        return f"{node_type}:{name}"

    def _ensure_node(
        self,
        node_type: str,
        name: str,
        class_ref: type | None = None,
        meta: dict[str, Any] | None = None,
    ) -> int:
        """
        Добавляет узел в граф, если его ещё нет. Возвращает индекс узла.

        Идемпотентен: если узел с таким ключом уже существует, возвращает
        его индекс без повторного добавления. Это критично для узлов
        context_field — если два аспекта запрашивают user.user_id,
        создаётся один узел и два ребра к нему.
        """
        key = self._make_node_key(node_type, name)
        if key in self._node_index:
            return self._node_index[key]

        payload = {
            "node_type": node_type,
            "name": name,
            "class_ref": class_ref,
            "meta": meta or {},
        }
        idx = self._graph.add_node(payload)
        self._node_index[key] = idx
        return idx

    def _add_edge_checked(
        self,
        source_idx: int,
        target_idx: int,
        edge_type: str,
    ) -> None:
        """
        Добавляет структурное ребро в граф с проверкой ацикличности.

        Используется ТОЛЬКО для рёбер depends и connection — типов,
        где реально возможны циклы (A зависит от B, B зависит от A).

        Для leaf-рёбер (has_aspect, has_checker, has_role, has_sensitive,
        subscribes, belongs_to, has_error_handler, requires_context)
        используется прямой self._graph.add_edge() без проверки —
        эти рёбра ведут к leaf-узлам без исходящих рёбер, цикл
        невозможен по конструкции.

        Исключения:
            CyclicDependencyError: если добавление ребра создаёт цикл.
        """
        edge_idx = self._graph.add_edge(source_idx, target_idx, edge_type)

        if not rx.is_directed_acyclic_graph(self._graph):  # pylint: disable=no-member
            self._graph.remove_edge_from_index(edge_idx)

            source_payload = self._graph[source_idx]
            target_payload = self._graph[target_idx]
            raise CyclicDependencyError(
                f"Обнаружена циклическая зависимость: добавление ребра "
                f"'{edge_type}' от '{source_payload['name']}' к "
                f"'{target_payload['name']}' создаёт цикл в графе. "
                f"Проверьте структуру зависимостей для этих классов."
            )

    def _add_leaf_edge(
        self,
        source_idx: int,
        target_idx: int,
        edge_type: str,
    ) -> None:
        """
        Добавляет leaf-ребро в граф БЕЗ проверки ацикличности.

        Leaf-рёбра ведут к узлам, не имеющим исходящих рёбер (aspect,
        checker, role, sensitive, subscription, domain, error_handler,
        context_field). Цикл невозможен по конструкции — target-узел
        никогда не ссылается обратно на source.

        Типы leaf-рёбер: has_aspect, has_checker, has_role, has_sensitive,
        subscribes, belongs_to, has_error_handler, requires_context.

        Аргументы:
            source_idx: индекс исходного узла.
            target_idx: индекс целевого узла (leaf).
            edge_type: тип ребра.
        """
        self._graph.add_edge(source_idx, target_idx, edge_type)

    def _determine_class_node_type(self, metadata: ClassMetadata) -> str:
        """
        Определяет тип узла для класса на основе его метаданных.

        Правила: подписки → plugin, аспекты → action, иначе → dependency.
        """
        if metadata.has_subscriptions():
            return "plugin"
        if metadata.has_aspects():
            return "action"
        return "dependency"

    def _build_class_meta(self, node_type: str, metadata: ClassMetadata) -> dict[str, Any]:
        """Формирует словарь метаданных для узла класса в графе."""
        description = metadata.meta.description if metadata.meta else ""
        domain_name = metadata.meta.domain.name if metadata.meta and metadata.meta.domain else None

        if node_type == "action":
            role_spec = metadata.role.spec if metadata.role else None
            return {
                "role": role_spec,
                "aspect_count": len(metadata.aspects),
                "error_handler_count": len(metadata.error_handlers),
                "description": description,
                "domain": domain_name,
            }
        if node_type == "plugin":
            return {
                "subscription_count": len(metadata.subscriptions),
                "description": description,
                "domain": domain_name,
            }
        return {
            "description": description,
            "domain": domain_name,
        }

    def _populate_domain_node(self, class_idx: int, metadata: ClassMetadata) -> None:
        """Создаёт узел домена и leaf-ребро belongs_to, если @meta указывает domain."""
        if metadata.meta is None or metadata.meta.domain is None:
            return

        domain_cls = metadata.meta.domain
        domain_name = domain_cls.name
        domain_idx = self._ensure_node(
            "domain", domain_name, class_ref=domain_cls,
            meta={"name": domain_name},
        )
        self._add_leaf_edge(class_idx, domain_idx, "belongs_to")

    def _populate_error_handlers(self, class_idx: int, class_name: str, metadata: ClassMetadata) -> None:
        """
        Создаёт узлы и leaf-рёбра для обработчиков ошибок (@on_error).

        Каждый обработчик — узел типа "error_handler" с атрибутами:
        exception_types (имена классов), method_name, description.
        Leaf-ребро "has_error_handler" от action к error_handler.

        Если обработчик имеет @context_requires (непустые context_keys),
        создаются дополнительные leaf-рёбра "requires_context" от узла
        обработчика к узлам context_field.
        """
        for handler_meta in metadata.error_handlers:
            handler_name = f"{class_name}.{handler_meta.method_name}"
            exc_type_names = [t.__name__ for t in handler_meta.exception_types]
            handler_idx = self._ensure_node(
                "error_handler", handler_name,
                meta={
                    "exception_types": exc_type_names,
                    "method_name": handler_meta.method_name,
                    "description": handler_meta.description,
                },
            )
            self._add_leaf_edge(class_idx, handler_idx, "has_error_handler")

            # Контекстные зависимости обработчика ошибок
            for ctx_key in sorted(handler_meta.context_keys):
                field_idx = self._ensure_node(
                    "context_field", ctx_key,
                    meta={"path": ctx_key},
                )
                self._add_leaf_edge(handler_idx, field_idx, "requires_context")

    def _populate_context_fields(self, class_name: str, metadata: ClassMetadata) -> None:
        """
        Создаёт узлы context_field и leaf-рёбра requires_context для аспектов.

        Для каждого аспекта с непустыми context_keys (из @context_requires)
        создаются рёбра от узла аспекта к узлам полей контекста.

        Узлы context_field переиспользуются через _ensure_node —
        если два аспекта запрашивают user.user_id, создаётся один
        узел и два ребра к нему.

        Рёбра requires_context — leaf-рёбра. Узлы context_field
        не имеют исходящих рёбер, цикл невозможен по конструкции.
        """
        for aspect_meta in metadata.aspects:
            if not aspect_meta.context_keys:
                continue

            aspect_key = self._make_node_key(
                "aspect", f"{class_name}.{aspect_meta.method_name}",
            )
            aspect_idx = self._node_index.get(aspect_key)
            if aspect_idx is None:
                continue

            for ctx_key in sorted(aspect_meta.context_keys):
                field_idx = self._ensure_node(
                    "context_field", ctx_key,
                    meta={"path": ctx_key},
                )
                self._add_leaf_edge(aspect_idx, field_idx, "requires_context")

    def _populate_graph(self, cls: type, metadata: ClassMetadata) -> None:
        """
        Заполняет граф узлами и рёбрами на основе метаданных класса.

        Добавляет узел класса, узлы и рёбра зависимостей, соединений,
        аспектов, чекеров, обработчиков ошибок (с их контекстными
        зависимостями), контекстных зависимостей аспектов, подписок,
        чувствительных полей, роли и домена.

        Структурные рёбра (depends, connection) проверяются на ацикличность
        через _add_edge_checked. Все остальные — leaf-рёбра, добавляются
        через _add_leaf_edge без проверки.
        """
        class_name = metadata.class_name
        node_type = self._determine_class_node_type(metadata)
        class_meta = self._build_class_meta(node_type, metadata)
        class_idx = self._ensure_node(node_type, class_name, class_ref=cls, meta=class_meta)

        # Домен (leaf-ребро belongs_to)
        self._populate_domain_node(class_idx, metadata)

        # Зависимости (структурное ребро depends — проверка ацикличности)
        for dep_info in metadata.dependencies:
            dep_name = _full_class_name(dep_info.cls)
            dep_idx = self._ensure_node(
                "dependency", dep_name, class_ref=dep_info.cls,
                meta={"description": dep_info.description},
            )
            self._add_edge_checked(class_idx, dep_idx, "depends")

        # Соединения (структурное ребро connection — проверка ацикличности)
        for conn_info in metadata.connections:
            conn_name = _full_class_name(conn_info.cls)
            conn_idx = self._ensure_node(
                "connection", conn_name, class_ref=conn_info.cls,
                meta={"key": conn_info.key, "description": conn_info.description},
            )
            self._add_edge_checked(class_idx, conn_idx, "connection")

        # Аспекты и их чекеры (leaf-рёбра)
        for aspect_meta in metadata.aspects:
            aspect_name = f"{class_name}.{aspect_meta.method_name}"
            aspect_idx = self._ensure_node(
                "aspect", aspect_name,
                meta={
                    "aspect_type": aspect_meta.aspect_type,
                    "description": aspect_meta.description,
                    "method_name": aspect_meta.method_name,
                },
            )
            self._add_leaf_edge(class_idx, aspect_idx, "has_aspect")

            for checker_meta in metadata.get_checkers_for_aspect(aspect_meta.method_name):
                checker_name = f"{aspect_name}.{checker_meta.field_name}"
                checker_idx = self._ensure_node(
                    "checker", checker_name,
                    meta={
                        "field_name": checker_meta.field_name,
                        "required": checker_meta.required,
                        "checker_class": checker_meta.checker_class.__name__,
                    },
                )
                self._add_leaf_edge(aspect_idx, checker_idx, "has_checker")

        # Контекстные зависимости аспектов (leaf-рёбра requires_context)
        self._populate_context_fields(class_name, metadata)

        # Обработчики ошибок и их контекстные зависимости (leaf-рёбра)
        self._populate_error_handlers(class_idx, class_name, metadata)

        # Подписки (leaf-рёбра)
        for i, sub_info in enumerate(metadata.subscriptions):
            sub_name = f"{class_name}.subscription_{i}_{sub_info.event_class.__name__}"
            sub_idx = self._ensure_node(
                "subscription", sub_name,
                meta={
                    "event_class": sub_info.event_class.__name__,
                    "action_name_pattern": sub_info.action_name_pattern,
                    "ignore_exceptions": sub_info.ignore_exceptions,
                    "method_name": sub_info.method_name,
                },
            )
            self._add_leaf_edge(class_idx, sub_idx, "subscribes")

        # Чувствительные поля (leaf-рёбра)
        for sf_meta in metadata.sensitive_fields:
            sf_name = f"{class_name}.{sf_meta.property_name}"
            sf_idx = self._ensure_node(
                "sensitive", sf_name,
                meta={
                    "property_name": sf_meta.property_name,
                    "config": dict(sf_meta.config),
                },
            )
            self._add_leaf_edge(class_idx, sf_idx, "has_sensitive")

        # Роль (leaf-ребро)
        if metadata.role is not None:
            role_name = f"{class_name}.role"
            role_idx = self._ensure_node(
                "role", role_name,
                meta={
                    "spec": metadata.role.spec,
                },
            )
            self._add_leaf_edge(class_idx, role_idx, "has_role")

    def _collect_linked_classes(self, metadata: ClassMetadata) -> None:
        """Рекурсивно обходит зависимости и соединения класса."""
        for dep_info in metadata.dependencies:
            self.get(dep_info.cls)
        for conn_info in metadata.connections:
            self.get(conn_info.cls)

    def _rebuild_graph(self) -> None:
        """Перестраивает граф из классов, оставшихся в кеше."""
        self._graph = rx.PyDiGraph()  # pylint: disable=no-member
        self._node_index = {}
        for cls, metadata in self._cache.items():
            self._populate_graph(cls, metadata)

    # ─────────────────────────────────────────────────────────────────────
    # Основной API: метаданные
    # ─────────────────────────────────────────────────────────────────────

    def get(self, cls: type) -> ClassMetadata:
        """
        Возвращает ClassMetadata для указанного класса.

        При первом вызове собирает метаданные через MetadataBuilder.build(),
        кеширует результат, проверяет strict-режим, заполняет граф
        и рекурсивно обходит зависимости.
        """
        if not isinstance(cls, type):
            raise TypeError(
                f"GateCoordinator.get() ожидает класс (type), "
                f"получен {type(cls).__name__}: {cls!r}"
            )

        if cls in self._cache:
            return self._cache[cls]

        metadata = MetadataBuilder.build(cls)

        self._validate_strict_domain(cls, metadata)

        # Помещаем в кеш ДО рекурсии — защита от циклов на уровне кеша
        self._cache[cls] = metadata

        self._populate_graph(cls, metadata)
        self._collect_linked_classes(metadata)

        return metadata

    def register(self, cls: type) -> ClassMetadata:
        """Явно регистрирует класс. Эквивалентен get()."""
        return self.get(cls)

    # ─────────────────────────────────────────────────────────────────────
    # Основной API: фабрики зависимостей
    # ─────────────────────────────────────────────────────────────────────

    def get_factory(self, cls: type) -> DependencyFactory:
        """Возвращает DependencyFactory для указанного класса."""
        if cls not in self._factory_cache:
            metadata = self.get(cls)
            self._factory_cache[cls] = DependencyFactory(metadata.dependencies)

        return self._factory_cache[cls]

    # ─────────────────────────────────────────────────────────────────────
    # Проверки и инвалидация
    # ─────────────────────────────────────────────────────────────────────

    def has(self, cls: type) -> bool:
        """Проверяет, есть ли метаданные класса в кеше."""
        return cls in self._cache

    def invalidate(self, cls: type) -> bool:
        """Удаляет метаданные и фабрику класса из кешей и перестраивает граф."""
        if cls not in self._cache:
            return False

        del self._cache[cls]
        self._factory_cache.pop(cls, None)

        self._rebuild_graph()

        return True

    def invalidate_all(self) -> int:
        """Полностью очищает все кеши, граф и индекс узлов."""
        count = len(self._cache)
        self._cache.clear()
        self._factory_cache.clear()
        self._graph = rx.PyDiGraph()  # pylint: disable=no-member
        self._node_index.clear()
        return count

    # ─────────────────────────────────────────────────────────────────────
    # Публичный API графа (только чтение)
    # ─────────────────────────────────────────────────────────────────────

    def get_graph(self) -> rx.PyDiGraph:  # pylint: disable=no-member
        """Возвращает копию графа."""
        return self._graph.copy()

    def get_node(self, key: str) -> dict[str, Any] | None:
        """
        Возвращает payload узла по ключу или None.

        Формат ключа: ``"тип:полное_имя"``.

        Примеры:
            >>> coordinator.get_node("action:module.CreateOrderAction")
            {"node_type": "action", "name": "module.CreateOrderAction", ...}

            >>> coordinator.get_node("context_field:user.user_id")
            {"node_type": "context_field", "name": "user.user_id",
             "meta": {"path": "user.user_id"}, ...}

            >>> coordinator.get_node("domain:orders")
            {"node_type": "domain", "name": "orders", ...}

            >>> coordinator.get_node("nonexistent:key")
            None
        """
        idx = self._node_index.get(key)
        if idx is None:
            return None
        return dict(self._graph[idx])

    def get_children(self, key: str) -> list[dict[str, Any]]:
        """
        Возвращает payload-ы прямых потомков узла.

        Формат ключа: ``"тип:полное_имя"``.

        Примеры:
            >>> coordinator.get_children("domain:orders")
            []  # домен — leaf-узел, потомков нет

            >>> coordinator.get_children("action:module.CreateOrderAction")
            [{"node_type": "aspect", ...}, {"node_type": "role", ...}, ...]

            >>> coordinator.get_children("aspect:module.CreateOrderAction.audit_aspect")
            [{"node_type": "context_field", "name": "user.user_id", ...}, ...]
        """
        idx = self._node_index.get(key)
        if idx is None:
            return []
        return [dict(self._graph[t]) for t in self._graph.successor_indices(idx)]

    def get_nodes_by_type(self, node_type: str) -> list[dict[str, Any]]:
        """
        Возвращает все узлы указанного типа.

        Примеры:
            >>> coordinator.get_nodes_by_type("context_field")
            [{"node_type": "context_field", "name": "user.user_id", ...},
             {"node_type": "context_field", "name": "request.trace_id", ...}]

            >>> coordinator.get_nodes_by_type("action")
            [{"node_type": "action", "name": "module.CreateOrderAction", ...}]
        """
        return [
            dict(self._graph[idx])
            for idx in self._graph.node_indices()
            if self._graph[idx].get("node_type") == node_type
        ]

    def get_dependency_tree(self, key: str) -> dict[str, Any]:
        """
        Возвращает полное дерево зависимостей узла в виде вложенного словаря.

        Формат ключа: ``"тип:полное_имя"``.

        Рекурсивно обходит все исходящие рёбра от узла. Каждый потомок
        содержит поле ``edge_type`` с типом ребра от родителя.
        Циклы обнаруживаются через множество visited и помечаются
        ``meta.cycle = True``.

        Пример:
            >>> coordinator.get_dependency_tree("action:module.CreateOrderAction")
            {
                "node_type": "action",
                "name": "module.CreateOrderAction",
                "meta": {...},
                "children": [
                    {"node_type": "aspect", "edge_type": "has_aspect", ...},
                    {"node_type": "dependency", "edge_type": "depends", ...},
                ]
            }
        """
        idx = self._node_index.get(key)
        if idx is None:
            return {}
        return self._build_tree_recursive(idx, set())

    def _build_tree_recursive(self, idx: int, visited: set[int]) -> dict[str, Any]:
        """Рекурсивно строит дерево зависимостей от указанного узла."""
        payload = self._graph[idx]

        node_result: dict[str, Any] = {
            "node_type": payload["node_type"],
            "name": payload["name"],
            "meta": dict(payload.get("meta", {})),
            "children": [],
        }

        if idx in visited:
            node_result["meta"]["cycle"] = True
            return node_result

        visited = visited | {idx}

        for _source, target, edge_data in self._graph.out_edges(idx):
            child_tree = self._build_tree_recursive(target, visited)
            child_tree["edge_type"] = edge_data
            node_result["children"].append(child_tree)

        return node_result

    # ─────────────────────────────────────────────────────────────────────
    # Инспекция
    # ─────────────────────────────────────────────────────────────────────

    def get_all_metadata(self) -> list[ClassMetadata]:
        """Возвращает список всех закешированных ClassMetadata."""
        return list(self._cache.values())

    def get_all_classes(self) -> list[type]:
        """Возвращает список всех зарегистрированных классов."""
        return list(self._cache.keys())

    @property
    def size(self) -> int:
        """Количество закешированных классов."""
        return len(self._cache)

    @property
    def graph_node_count(self) -> int:
        """Количество узлов в графе."""
        return self._graph.num_nodes()

    @property
    def graph_edge_count(self) -> int:
        """Количество рёбер в графе."""
        return self._graph.num_edges()

    # ─────────────────────────────────────────────────────────────────────
    # Удобные методы (делегирование к ClassMetadata)
    # ─────────────────────────────────────────────────────────────────────

    def get_dependencies(self, cls: type) -> tuple[Any, ...]:
        """Возвращает кортеж зависимостей класса."""
        return self.get(cls).dependencies

    def get_connections(self, cls: type) -> tuple[Any, ...]:
        """Возвращает кортеж соединений класса."""
        return self.get(cls).connections

    def get_role(self, cls: type) -> RoleMeta | None:
        """Возвращает RoleMeta класса или None."""
        return self.get(cls).role

    def get_aspects(self, cls: type) -> tuple[Any, ...]:
        """Возвращает кортеж аспектов класса."""
        return self.get(cls).aspects

    def get_subscriptions(self, cls: type) -> tuple[Any, ...]:
        """Возвращает кортеж подписок класса (для плагинов)."""
        return self.get(cls).subscriptions

    def get_meta(self, cls: type) -> MetaInfo | None:
        """Возвращает MetaInfo класса или None."""
        return self.get(cls).meta

    # ─────────────────────────────────────────────────────────────────────
    # Строковое представление
    # ─────────────────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        """Компактное строковое представление для отладки."""
        if not self._cache:
            return f"GateCoordinator(empty, strict={self._strict})"

        class_names = ", ".join(
            meta.class_name for meta in self._cache.values()
        )
        return (
            f"GateCoordinator(size={self.size}, "
            f"nodes={self.graph_node_count}, "
            f"edges={self.graph_edge_count}, "
            f"strict={self._strict}, "
            f"classes=[{class_names}])"
        )
