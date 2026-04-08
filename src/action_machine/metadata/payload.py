# src/action_machine/metadata/payload.py
"""
Транспортные объекты для передачи данных между гейтхостами и координатором.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Модуль содержит два frozen-датакласса, образующих контракт между
гейтхостами (AbstractGateHost) и координатором (GateCoordinator):

1. EdgeInfo — описание одного ребра графа, исходящего из узла.
2. FacetPayload — полное описание одного узла графа с его рёбрами.

Оба объекта являются транспортными: они создаются гейтхостом в методе
_build_payload(), передаются координатору в build(), и после коммита
в граф выбрасываются. В граф данные попадают как обычные dict —
конвертация tuple → dict происходит один раз при коммите.

═══════════════════════════════════════════════════════════════════════════════
ИММУТАБЕЛЬНОСТЬ
═══════════════════════════════════════════════════════════════════════════════

Оба датакласса frozen=True. После создания ни одно поле изменить нельзя.
Это гарантирует, что данные, собранные гейтхостом, не будут случайно
модифицированы между фазами build() координатора (сбор → проверки → коммит).

Поля node_meta и edge_meta имеют тип tuple[tuple[str, Any], ...] вместо
dict[str, Any]. Причина: frozen dataclass должен быть хешируемым, а dict
не хешируем. tuple of tuples — иммутабельная и хешируемая альтернатива.
Конвертация в dict выполняется координатором один раз при коммите.

═══════════════════════════════════════════════════════════════════════════════
ДВА ТИПА РЁБЕР
═══════════════════════════════════════════════════════════════════════════════

Рёбра графа делятся на два типа по полю is_structural:

    is_structural=True  — структурные рёбра (depends, connection).
        Образуют скелет системы. Циклы запрещены. Координатор проверяет
        ацикличность на фазе 2 через симуляцию на временном графе.
        Цикл → InvalidGraphError.

    is_structural=False — информационные рёбра (has_aspect, belongs_to,
        requires_context, has_checker, subscribes и т.д.).
        Несут метаданные. Циклы допустимы (например, двусторонние связи
        сущностей). Координатор не проверяет ацикличность для них.

═══════════════════════════════════════════════════════════════════════════════
ФОРМАТ КЛЮЧЕЙ УЗЛОВ
═══════════════════════════════════════════════════════════════════════════════

Каждый узел графа идентифицируется строковым ключом формата "тип:имя".
Гейтхост формирует только имя (node_name) через хелпер _make_node_name().
Координатор собирает полный ключ "node_type:node_name" самостоятельно.

    node_type = "action",  node_name = "module.CreateOrderAction"
    → ключ в графе: "action:module.CreateOrderAction"

    node_type = "role",    node_name = "module.CreateOrderAction"
    → ключ в графе: "role:module.CreateOrderAction"

Один класс может порождать несколько узлов разных типов от разных
гейтхостов. Например, CreateOrderAction порождает узел "action:..." от
DependencyGateHost и узел "role:..." от RoleGateHost. Ключи уникальны
благодаря префиксу типа.

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ЖИЗНЕННОГО ЦИКЛА
═══════════════════════════════════════════════════════════════════════════════

    # 1. Гейтхост создаёт payload в _build_payload():
    payload = FacetPayload(
        node_type="role",
        node_name="module.CreateOrderAction",
        node_class=CreateOrderAction,
        node_meta=(("spec", "admin"),),
        edges=(),
    )

    # 2. Координатор собирает все payload в фазе 1 (сбор).

    # 3. Координатор проверяет payload в фазе 2 (проверки):
    #    - node_type и node_name непустые
    #    - node_class — тип
    #    - ключи уникальны
    #    - цели рёбер существуют
    #    - структурные рёбра ацикличны

    # 4. Координатор коммитит в граф в фазе 3:
    #    graph.add_node({
    #        "node_type": "role",
    #        "name": "module.CreateOrderAction",
    #        "class_ref": CreateOrderAction,
    #        "meta": {"spec": "admin"},
    #    })

    # 5. payload выбрасывается. Граф — единственный источник правды.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class EdgeInfo:
    """
    Описание одного ребра графа, исходящего из узла.

    Создаётся гейтхостом через хелпер AbstractGateHost._make_edge().
    Передаётся координатору внутри FacetPayload.edges. Координатор
    использует EdgeInfo для проверки ссылочной целостности (цель
    существует) и ацикличности (для структурных рёбер).

    Атрибуты:
        target_node_type : str
            Тип целевого узла ("action", "entity", "domain" и т.д.).
            Используется координатором для формирования полного ключа
            цели: "target_node_type:target_name".

        target_name : str
            Имя целевого узла (формат "module.ClassName" или
            "module.ClassName.suffix"). Формируется гейтхостом
            через _make_node_name().

        edge_type : str
            Тип ребра: "depends", "connection", "has_aspect",
            "belongs_to", "requires_context", "has_checker",
            "subscribes", "has_error_handler", "has_compensator",
            "has_sensitive", "has_role", "has_field",
            "has_relation", "has_lifecycle".

        is_structural : bool
            True — структурное ребро. Циклы запрещены.
            False — информационное ребро. Циклы допустимы.

        edge_meta : tuple[tuple[str, Any], ...]
            Дополнительные метаданные ребра в формате tuple of tuples.
            Конвертируется в dict при коммите в граф.
            Пустой tuple по умолчанию.
    """

    target_node_type: str
    target_name: str
    edge_type: str
    is_structural: bool
    edge_meta: tuple[tuple[str, Any], ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class FacetPayload:
    """
    Полное описание одного узла графа с его исходящими рёбрами.

    Создаётся гейтхостом в методе _build_payload(). Один вызов
    inspect() → один FacetPayload (или None если класс не подходит).
    Координатор собирает все payload от всех гейтхостов в фазе 1,
    проверяет в фазе 2 и коммитит в граф в фазе 3.

    Один класс может порождать несколько FacetPayload от разных
    гейтхостов. Например, CreateOrderAction порождает:
    - FacetPayload(node_type="role", ...) от RoleGateHost
    - FacetPayload(node_type="action", ..., edges=[depends...]) от DependencyGateHost
    - FacetPayload(node_type="aspect", ...) от AspectGateHost (для каждого аспекта)

    Уникальность гарантируется комбинацией node_type + node_name.

    Атрибуты:
        node_type : str
            Тип узла в графе: "action", "role", "aspect", "checker",
            "entity", "domain", "dependency", "connection",
            "error_handler", "compensator", "subscription",
            "sensitive", "context_field", "entity_field",
            "entity_relation", "entity_lifecycle".

        node_name : str
            Имя узла без префикса типа. Формат "module.ClassName"
            или "module.ClassName.suffix". Формируется гейтхостом
            через _make_node_name(). Координатор собирает полный
            ключ "node_type:node_name".

        node_class : type
            Ссылка на класс Python, породивший этот узел.
            Используется координатором для хранения в графе
            и для рантайм-доступа к классу.

        node_meta : tuple[tuple[str, Any], ...]
            Метаданные узла, специфичные для гейтхоста.
            Формат: tuple of (key, value) пар.
            Конвертируется в dict при коммите в граф.
            Содержимое зависит от гейтхоста:
            - RoleGateHost: (("spec", "admin"),)
            - AspectGateHost: (("aspect_type", "regular"), ("method_name", "validate"), ...)
            - EntityGateHost: (("description", "Заказ"), ("domain", "shop"), ...)
            Пустой tuple по умолчанию.

        edges : tuple[EdgeInfo, ...]
            Исходящие рёбра от этого узла. Каждое ребро описывает
            связь с другим узлом графа. Гейтхосты без рёбер
            (например, RoleGateHost) возвращают пустой tuple.
            Пустой tuple по умолчанию.
    """

    node_type: str
    node_name: str
    node_class: type
    node_meta: tuple[tuple[str, Any], ...] = field(default_factory=tuple)
    edges: tuple[EdgeInfo, ...] = field(default_factory=tuple)
