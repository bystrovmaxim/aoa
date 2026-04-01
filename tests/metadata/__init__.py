# tests/metadata/__init__.py
"""
Пакет тестов метаданных ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Содержит тесты для системы метаданных — центрального механизма,
связывающего декораторы, классы действий и координатор. Метаданные
собираются из атрибутов классов (установленных декораторами) и
описывают полную конфигурацию каждого зарегистрированного компонента.

═══════════════════════════════════════════════════════════════════════════════
КОМПОНЕНТЫ
═══════════════════════════════════════════════════════════════════════════════

ClassMetadata
    Frozen-датакласс, хранящий полную конфигурацию одного класса:
    class_ref, class_name, meta (MetaInfo), role (RoleMeta),
    dependencies, connections, aspects, checkers, subscriptions,
    sensitive_fields, params_fields, result_fields. Предоставляет
    хелперы: has_role, has_dependencies, has_connections, has_aspects,
    get_regular_aspects, get_summary_aspect, get_checkers_for_aspect,
    get_dependency_classes, get_connection_keys.

MetadataBuilder
    Собирает ClassMetadata из класса, обходя его атрибуты и методы.
    Вызывает коллекторы (collect_meta, collect_role, collect_dependencies,
    collect_connections, collect_aspects, collect_checkers,
    collect_subscriptions, collect_sensitive_fields) и валидаторы
    (validate_aspects, validate_gate_hosts, validate_meta_required,
    validate_described_fields, validate_checkers_belong_to_aspects).

GateCoordinator
    Реестр метаданных. Кеширует ClassMetadata по классу,
    строит направленный граф зависимостей (nodes, edges),
    обнаруживает циклы, поддерживает strict mode (обязательный domain),
    предоставляет публичное API (get, register, has, invalidate,
    invalidate_all, get_graph, get_node, get_children, get_nodes_by_type,
    get_dependency_tree, get_factory).

BaseDomain
    Абстрактный базовый класс для доменов. Валидирует атрибут name
    при наследовании: обязателен, строка, не пустой. Используется
    в @meta(description, domain=SomeDomain) для группировки компонентов.

═══════════════════════════════════════════════════════════════════════════════
СТРУКТУРА ТЕСТОВ
═══════════════════════════════════════════════════════════════════════════════

    tests/metadata/
    ├── __init__.py                     — этот файл
    ├── test_class_metadata.py          — ClassMetadata: создание, immutability, хелперы, repr
    ├── test_builder_basic.py           — MetadataBuilder: пустой класс, роль, зависимости, соединения
    ├── test_builder_aspects.py         — MetadataBuilder: аспекты, структурные инварианты
    ├── test_builder_checkers.py        — MetadataBuilder: чекеры на аспектах
    ├── test_builder_inheritance.py     — MetadataBuilder: наследование метаданных
    ├── test_builder_sensitive.py       — MetadataBuilder: sensitive fields, subscriptions
    ├── test_coordinator_graph.py       — GateCoordinator: граф, узлы, рёбра, циклы, API
    ├── test_coordinator_strict.py      — GateCoordinator: strict mode, домены в графе
    └── test_domain.py                  — BaseDomain: валидация name, наследование, изоляция
"""
