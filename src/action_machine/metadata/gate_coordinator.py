# src/action_machine/metadata/gate_coordinator.py
"""
GateCoordinator — центральный реестр и сборщик графа зависимостей системы.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

GateCoordinator — единственная точка входа для построения и чтения графа
всех сущностей системы ActionMachine. Координатор:

1. Принимает регистрацию инспекторов гейтхостов через fluent-метод register().
2. Строит граф один раз при вызове build() через транзакционный трёхфазный
   процесс.
3. Предоставляет типизированные методы чтения данных из графа для рантайма
   (машина, адаптеры, плагины).

После build() граф становится единственным источником правды. Координатор
только читает граф, никогда не модифицирует его после коммита.

═══════════════════════════════════════════════════════════════════════════════
ТРАНЗАКЦИОННЫЙ build() — ТРИ ФАЗЫ
═══════════════════════════════════════════════════════════════════════════════

Граф либо строится полностью и корректно, либо не строится вообще.
Никакого частичного состояния.

    ФАЗА 1 — СБОР
        Для каждого зарегистрированного инспектора обходятся наследники
        его маркерного миксина (_subclasses_recursive). Для каждого
        наследника вызывается inspect(). Результат (FacetPayload или None)
        накапливается в список. Граф не трогается.

    ФАЗА 2 — ПРОВЕРКИ
        Все собранные payload проверяются на:
        2a. Обязательные поля непустые (PayloadValidationError).
        2b. Уникальность ключей "node_type:node_name" (DuplicateNodeError).
        2c. Ссылочная целостность рёбер — цель существует (InvalidGraphError).
        2d. Ацикличность структурных рёбер через симуляцию на временном
            графе (InvalidGraphError).
        Граф не трогается.

    ФАЗА 3 — КОММИТ
        Только если фаза 2 прошла. Все узлы и рёбра добавляются в граф.
        tuple of tuples конвертируется в dict. Флаг _built = True.

═══════════════════════════════════════════════════════════════════════════════
РАЗДЕЛЕНИЕ ВАЛИДАЦИИ
═══════════════════════════════════════════════════════════════════════════════

    Декораторы (@check_roles, @regular_aspect, @depends...)
        Проверяют аргументы при import-time. Типы, пустоту, issubclass.
        Ошибки обнаруживаются немедленно при определении класса.

    Координатор (build(), фаза 2)
        Глобальные структурные проверки: уникальность ключей, ссылочная
        целостность, ацикличность. Одно место для всех проверок графа.

Логика проверки не размазывается. Декоратор отвечает за свои аргументы,
координатор — за целостность графа.

═══════════════════════════════════════════════════════════════════════════════
ОГРАНИЧЕНИЯ
═══════════════════════════════════════════════════════════════════════════════

- build() вызывается ровно один раз. Повторный вызов → RuntimeError.
- register() после build() → RuntimeError.
- Дубликат инспектора при register() → ValueError.

═══════════════════════════════════════════════════════════════════════════════
ФОРМАТ КЛЮЧЕЙ УЗЛОВ
═══════════════════════════════════════════════════════════════════════════════

Каждый узел графа идентифицируется строковым ключом "node_type:node_name".
Инспектор формирует node_type и node_name. Координатор собирает ключ:

    node_type="role", node_name="module.CreateOrderAction"
    → ключ: "role:module.CreateOrderAction"

Один класс может порождать несколько узлов от разных инспекторов.
Уникальность гарантируется комбинацией node_type + node_name.

═══════════════════════════════════════════════════════════════════════════════
ГРАФ
═══════════════════════════════════════════════════════════════════════════════

Граф построен на библиотеке rustworkx (rx.PyDiGraph). Узлы хранят dict
с полями: node_type, name, class_ref, meta. Рёбра хранят dict с полями:
edge_type, meta.

═══════════════════════════════════════════════════════════════════════════════
РАНТАЙМ-ДОСТУП
═══════════════════════════════════════════════════════════════════════════════

Координатор предоставляет типизированные методы чтения данных из графа.
Машина (ActionProductMachine) и адаптеры используют эти методы вместо
прямого доступа к ClassMetadata.

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.metadata.gate_coordinator import GateCoordinator
    from action_machine.auth.role_gate_host_inspector import RoleGateHostInspector
    from action_machine.aspects.aspect_gate_host_inspector import AspectGateHostInspector

    coordinator = (
        GateCoordinator(strict=True)
        .register(RoleGateHostInspector)
        .register(AspectGateHostInspector)
        .build()
    )

    # Рантайм-доступ:
    spec = coordinator.get_role_spec(CreateOrderAction)
    aspects = coordinator.get_regular_aspects(CreateOrderAction)
"""

from __future__ import annotations

from typing import Any

import rustworkx as rx

from action_machine.metadata.base_gate_host_inspector import BaseGateHostInspector
from action_machine.metadata.exceptions import (
    DuplicateNodeError,
    InvalidGraphError,
    PayloadValidationError,
)
from action_machine.metadata.payload import FacetPayload


class GateCoordinator:
    """
    Центральный реестр и сборщик графа зависимостей системы ActionMachine.

    Принимает регистрацию инспекторов, строит граф через транзакционный
    build() и предоставляет типизированные методы чтения.

    Атрибуты:
        _strict : bool
            Если True — дополнительные проверки при build()
            (например, обязательность domain в @meta для Action).

        _inspectors : list[type[BaseGateHostInspector]]
            Зарегистрированные инспекторы в порядке регистрации.

        _registered : set[type[BaseGateHostInspector]]
            Множество зарегистрированных инспекторов для проверки
            дубликатов.

        _graph : rx.PyDiGraph
            Направленный граф сущностей системы. Заполняется
            при коммите (фаза 3). После build() — только чтение.

        _node_index : dict[str, int]
            Карта ключ_узла → индекс_в_графе. Заполняется при коммите.

        _class_index : dict[type, list[str]]
            Карта класс → список ключей узлов, порождённых этим классом.
            Заполняется при коммите. Используется рантайм-методами
            для поиска узлов по классу.

        _built : bool
            Флаг завершения build(). После True — register() запрещён,
            повторный build() запрещён.
    """

    def __init__(self, strict: bool = False) -> None:
        """
        Создаёт координатор с пустым графом.

        Аргументы:
            strict: если True — дополнительные проверки при build().
        """
        self._strict: bool = strict
        self._inspectors: list[type[BaseGateHostInspector]] = []
        self._registered: set[type[BaseGateHostInspector]] = set()
        self._graph: rx.PyDiGraph = rx.PyDiGraph()
        self._node_index: dict[str, int] = {}
        self._class_index: dict[type, list[str]] = {}
        self._built: bool = False

    # ═══════════════════════════════════════════════════════════════════
    # Fluent-регистрация инспекторов
    # ═══════════════════════════════════════════════════════════════════

    def register(
        self, inspector_cls: type[BaseGateHostInspector],
    ) -> GateCoordinator:
        """
        Регистрирует инспектор гейтхоста.

        Вызывается до build(). Поддерживает fluent-цепочку:

            coordinator = GateCoordinator()\\
                .register(RoleGateHostInspector)\\
                .register(AspectGateHostInspector)\\
                .build()

        Аргументы:
            inspector_cls: класс инспектора (наследник BaseGateHostInspector).

        Возвращает:
            self — для fluent-цепочки.

        Исключения:
            RuntimeError: если build() уже вызван.
            ValueError: если инспектор уже зарегистрирован.
        """
        if self._built:
            raise RuntimeError(
                f"Регистрация {inspector_cls.__name__} после build() запрещена. "
                f"Все инспекторы регистрируются до вызова build()."
            )
        if inspector_cls in self._registered:
            raise ValueError(
                f"Инспектор {inspector_cls.__name__} уже зарегистрирован."
            )
        self._inspectors.append(inspector_cls)
        self._registered.add(inspector_cls)
        return self

    # ═══════════════════════════════════════════════════════════════════
    # Построение графа
    # ═══════════════════════════════════════════════════════════════════

    def build(self) -> GateCoordinator:
        """
        Транзакционное построение графа.

        Вызывается ровно один раз после регистрации всех инспекторов.
        Три фазы: сбор → проверки → коммит. Если любая проверка
        не прошла — граф не изменяется, исключение пробрасывается.

        Возвращает:
            self — для fluent-цепочки (coordinator = GateCoordinator()...build()).

        Исключения:
            RuntimeError: если build() уже вызван.
            PayloadValidationError: невалидные поля payload (фаза 2a).
            DuplicateNodeError: конфликт ключей узлов (фаза 2b).
            InvalidGraphError: битая ссылка ребра или цикл (фаза 2c, 2d).
        """
        if self._built:
            raise RuntimeError(
                "build() уже вызван. Координатор строит граф один раз."
            )

        all_payloads, payload_sources = self._phase1_collect()
        self._phase2_check_payloads(all_payloads)
        self._phase2_check_key_uniqueness(all_payloads, payload_sources)
        self._phase2_check_referential_integrity(all_payloads)
        self._phase2_check_acyclicity(all_payloads)
        self._phase3_commit(all_payloads)

        self._built = True
        return self

    # ═══════════════════════════════════════════════════════════════════
    # Фаза 1 — Сбор
    # ═══════════════════════════════════════════════════════════════════

    def _phase1_collect(
        self,
    ) -> tuple[list[FacetPayload], dict[str, str]]:
        """
        Обходит всех инспекторов и собирает FacetPayload.

        Для каждого инспектора вызывает _subclasses_recursive(), затем
        inspect() для каждого найденного класса. payload с None
        отфильтровываются.

        Дополнительно отслеживает, какой инспектор создал каждый payload,
        для информативных сообщений об ошибках в фазе 2.

        Возвращает:
            Кортеж из двух элементов:
            - list[FacetPayload] — все собранные payload.
            - dict[str, str] — карта ключ_узла → имя_инспектора
              (для сообщений об ошибках DuplicateNodeError).
        """
        all_payloads: list[FacetPayload] = []
        payload_sources: dict[str, str] = {}

        for inspector_cls in self._inspectors:
            inspector_name = inspector_cls.__name__
            subclasses = inspector_cls._subclasses_recursive()

            for target_cls in subclasses:
                payload = inspector_cls.inspect(target_cls)
                if payload is None:
                    continue

                key = self._make_key(payload.node_type, payload.node_name)

                if key in payload_sources:
                    raise DuplicateNodeError(
                        key=key,
                        first_gate_host=payload_sources[key],
                        second_gate_host=inspector_name,
                    )

                payload_sources[key] = inspector_name
                all_payloads.append(payload)

        return all_payloads, payload_sources

    # ═══════════════════════════════════════════════════════════════════
    # Фаза 2 — Проверки
    # ═══════════════════════════════════════════════════════════════════

    def _phase2_check_payloads(
        self, payloads: list[FacetPayload],
    ) -> None:
        """
        Проверка 2a: обязательные поля payload непустые.

        Каждый payload должен иметь:
        - node_type — непустая строка.
        - node_name — непустая строка.
        - node_class — экземпляр type.

        Аргументы:
            payloads: список payload для проверки.

        Исключения:
            PayloadValidationError: если любое обязательное поле невалидно.
        """
        for p in payloads:
            if not p.node_type:
                raise PayloadValidationError(
                    node_class=p.node_class,
                    field_name="node_type",
                    detail="пустая строка",
                )
            if not p.node_name:
                raise PayloadValidationError(
                    node_class=p.node_class,
                    field_name="node_name",
                    detail="пустая строка",
                )
            if not isinstance(p.node_class, type):
                raise PayloadValidationError(
                    node_class=p.node_class,
                    field_name="node_class",
                    detail=f"ожидался type, получен {type(p.node_class).__name__}",
                )

    def _phase2_check_key_uniqueness(
        self,
        payloads: list[FacetPayload],
        payload_sources: dict[str, str],
    ) -> None:
        """
        Проверка 2b: уникальность ключей узлов.

        Дубликаты уже обнаруживаются в _phase1_collect при заполнении
        payload_sources. Этот метод — дополнительная защита на случай
        если payload_sources не используется (прямой вызов фазы 2
        в тестах).

        Аргументы:
            payloads: список payload для проверки.
            payload_sources: карта ключ → имя инспектора.

        Исключения:
            DuplicateNodeError: если обнаружен дубликат ключа.
        """
        seen: set[str] = set()
        for p in payloads:
            key = self._make_key(p.node_type, p.node_name)
            if key in seen:
                raise DuplicateNodeError(
                    key=key,
                    first_gate_host=payload_sources.get(key, "unknown"),
                    second_gate_host="unknown",
                )
            seen.add(key)

    def _phase2_check_referential_integrity(
        self, payloads: list[FacetPayload],
    ) -> None:
        """
        Проверка 2c: ссылочная целостность рёбер.

        Каждое ребро ссылается на целевой узел через
        "target_node_type:target_name". Этот ключ обязан существовать
        среди собранных payload. Если цель не найдена — ребро битое.

        Аргументы:
            payloads: список payload для проверки.

        Исключения:
            InvalidGraphError: если ребро ссылается на несуществующий узел.
        """
        all_keys: set[str] = {
            self._make_key(p.node_type, p.node_name)
            for p in payloads
        }

        for p in payloads:
            source_key = self._make_key(p.node_type, p.node_name)
            for edge in p.edges:
                target_key = self._make_key(
                    edge.target_node_type, edge.target_name,
                )
                if target_key not in all_keys:
                    raise InvalidGraphError(
                        f"Ребро '{edge.edge_type}' из '{source_key}' "
                        f"ссылается на несуществующий узел '{target_key}'. "
                        f"Класс-цель не обнаружен ни одним инспектором."
                    )

    def _phase2_check_acyclicity(
        self, payloads: list[FacetPayload],
    ) -> None:
        """
        Проверка 2d: ацикличность структурных рёбер.

        Создаёт временный граф, добавляет только структурные рёбра
        (is_structural=True) и проверяет ацикличность через
        rustworkx.is_directed_acyclic_graph().

        Информационные рёбра (is_structural=False) не проверяются —
        циклические связи между сущностями допустимы.

        Аргументы:
            payloads: список payload для проверки.

        Исключения:
            InvalidGraphError: если структурные рёбра образуют цикл.
        """
        test_graph: rx.PyDiGraph = rx.PyDiGraph()
        test_index: dict[str, int] = {}

        for p in payloads:
            key = self._make_key(p.node_type, p.node_name)
            idx = test_graph.add_node(key)
            test_index[key] = idx

        has_structural_edges = False
        for p in payloads:
            source_key = self._make_key(p.node_type, p.node_name)
            source_idx = test_index[source_key]
            for edge in p.edges:
                if not edge.is_structural:
                    continue
                target_key = self._make_key(
                    edge.target_node_type, edge.target_name,
                )
                target_idx = test_index[target_key]
                test_graph.add_edge(source_idx, target_idx, edge.edge_type)
                has_structural_edges = True

        if has_structural_edges and not rx.is_directed_acyclic_graph(test_graph):
            raise InvalidGraphError(
                "Структурные рёбра (depends, connection) образуют цикл. "
                "Проверьте зависимости между классами."
            )

    # ═══════════════════════════════════════════════════════════════════
    # Фаза 3 — Коммит
    # ═══════════════════════════════════════════════════════════════════

    def _phase3_commit(self, payloads: list[FacetPayload]) -> None:
        """
        Коммит всех payload в граф.

        Выполняется только если фаза 2 прошла полностью.
        Конвертирует tuple of tuples в dict для хранения в узлах графа.
        Заполняет _node_index и _class_index.

        Аргументы:
            payloads: список провалидированных payload.
        """
        # Добавляем все узлы
        for p in payloads:
            key = self._make_key(p.node_type, p.node_name)
            idx = self._graph.add_node({
                "node_type": p.node_type,
                "name": p.node_name,
                "class_ref": p.node_class,
                "meta": dict(p.node_meta),
            })
            self._node_index[key] = idx

            # Заполняем class_index
            if p.node_class not in self._class_index:
                self._class_index[p.node_class] = []
            self._class_index[p.node_class].append(key)

        # Добавляем все рёбра
        for p in payloads:
            source_key = self._make_key(p.node_type, p.node_name)
            source_idx = self._node_index[source_key]
            for edge in p.edges:
                target_key = self._make_key(
                    edge.target_node_type, edge.target_name,
                )
                target_idx = self._node_index[target_key]
                self._graph.add_edge(source_idx, target_idx, {
                    "edge_type": edge.edge_type,
                    "meta": dict(edge.edge_meta),
                })

    # ═══════════════════════════════════════════════════════════════════
    # Утилиты
    # ═══════════════════════════════════════════════════════════════════

    @staticmethod
    def _make_key(node_type: str, name: str) -> str:
        """
        Формирует уникальный ключ узла: "node_type:name".

        Аргументы:
            node_type: тип узла ("role", "action", "entity" и т.д.).
            name: имя узла ("module.ClassName").

        Возвращает:
            str — ключ вида "role:module.CreateOrderAction".
        """
        return f"{node_type}:{name}"

    # ═══════════════════════════════════════════════════════════════════
    # Публичные свойства
    # ═══════════════════════════════════════════════════════════════════

    @property
    def strict(self) -> bool:
        """Возвращает strict-режим координатора."""
        return self._strict

    @property
    def is_built(self) -> bool:
        """True если build() уже вызван."""
        return self._built

    @property
    def graph_node_count(self) -> int:
        """Количество узлов в графе."""
        return self._graph.num_nodes()

    @property
    def graph_edge_count(self) -> int:
        """Количество рёбер в графе."""
        return self._graph.num_edges()

    # ═══════════════════════════════════════════════════════════════════
    # Чтение графа — низкоуровневые методы
    # ═══════════════════════════════════════════════════════════════════

    def has_node(self, node_type: str, name: str) -> bool:
        """
        Проверяет существование узла в графе.

        Аргументы:
            node_type: тип узла.
            name: имя узла.

        Возвращает:
            True если узел существует.
        """
        return self._make_key(node_type, name) in self._node_index

    def get_node(self, node_type: str, name: str) -> dict[str, Any] | None:
        """
        Возвращает payload узла по типу и имени.

        Аргументы:
            node_type: тип узла.
            name: имя узла.

        Возвращает:
            dict с полями node_type, name, class_ref, meta.
            None если узел не найден.
        """
        key = self._make_key(node_type, name)
        idx = self._node_index.get(key)
        if idx is None:
            return None
        return dict(self._graph[idx])

    def get_nodes_by_type(self, node_type: str) -> list[dict[str, Any]]:
        """
        Возвращает все узлы указанного типа.

        Аргументы:
            node_type: тип узлов для поиска.

        Возвращает:
            Список dict с данными узлов.
        """
        return [
            dict(self._graph[idx])
            for idx in self._graph.node_indices()
            if self._graph[idx].get("node_type") == node_type
        ]

    def get_nodes_for_class(self, cls: type) -> list[dict[str, Any]]:
        """
        Возвращает все узлы графа, порождённые указанным классом.

        Один класс может порождать несколько узлов от разных инспекторов
        (например, "role:...", "action:...", "aspect:...").

        Аргументы:
            cls: класс Python.

        Возвращает:
            Список dict с данными узлов. Пустой список если класс
            не порождал узлов.
        """
        keys = self._class_index.get(cls, [])
        result: list[dict[str, Any]] = []
        for key in keys:
            idx = self._node_index.get(key)
            if idx is not None:
                result.append(dict(self._graph[idx]))
        return result

    def get_node_meta(
        self, cls: type, node_type: str,
    ) -> dict[str, Any] | None:
        """
        Возвращает meta узла указанного типа для класса.

        Ищет среди узлов, порождённых cls, узел с node_type.
        Возвращает его meta как dict.

        Аргументы:
            cls: класс Python.
            node_type: тип искомого узла.

        Возвращает:
            dict с метаданными узла. None если узел не найден.
        """
        name = BaseGateHostInspector._make_node_name(cls)
        node = self.get_node(node_type, name)
        if node is None:
            return None
        return node.get("meta")

    def get_graph(self) -> rx.PyDiGraph:
        """
        Возвращает копию графа.

        Копия — чтобы внешний код не мог модифицировать граф.

        Возвращает:
            rx.PyDiGraph — копия направленного графа.
        """
        return self._graph.copy()

    # ═══════════════════════════════════════════════════════════════════
    # Рантайм-доступ — типизированные методы
    # ═══════════════════════════════════════════════════════════════════

    def get_role_spec(self, cls: type) -> Any:
        """
        Возвращает ролевую спецификацию класса.

        Читает spec из node_meta узла типа "role" для указанного класса.

        Аргументы:
            cls: класс Action.

        Возвращает:
            str | list[str] — спецификация ролей.
            None — если класс не имеет @check_roles.
        """
        meta = self.get_node_meta(cls, "role")
        if meta is None:
            return None
        return meta.get("spec")

    # ═══════════════════════════════════════════════════════════════════
    # Строковое представление
    # ═══════════════════════════════════════════════════════════════════

    def __repr__(self) -> str:
        """Компактное строковое представление для отладки."""
        state = "built" if self._built else "not built"
        inspector_names = ", ".join(i.__name__ for i in self._inspectors)
        return (
            f"GateCoordinator("
            f"state={state}, "
            f"strict={self._strict}, "
            f"inspectors=[{inspector_names}], "
            f"nodes={self.graph_node_count}, "
            f"edges={self.graph_edge_count})"
        )
