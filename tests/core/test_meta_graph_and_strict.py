# tests/core/test_meta_graph_and_strict.py
"""
Тесты интеграции @meta с графом GateCoordinator и strict-режимом.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

Граф — доменные узлы и рёбра belongs_to:
    - Action с domain → узел "domain" создаётся, ребро "belongs_to" есть.
    - Два Action в одном домене → один узел "domain", два ребра belongs_to.
    - Action без domain → узел "domain" не создаётся.
    - ResourceManager с domain → узел "domain" создаётся.
    - Payload узлов action и dependency содержит description и domain.

Граф — описание в payload:
    - description из @meta попадает в meta узла action.
    - description из @meta попадает в meta узла dependency (ResourceManager).
    - Отсутствие @meta → description пустая строка в payload.

Strict-режим:
    - strict=True, Action с domain → OK.
    - strict=True, Action без domain → ValueError.
    - strict=True, ResourceManager с domain → OK.
    - strict=True, ResourceManager без domain → ValueError.
    - strict=False, Action без domain → OK (нет ошибки).
    - strict=False, ResourceManager без domain → OK.
    - Обычный класс без гейт-хоста → strict не влияет.
    - Свойство coordinator.strict возвращает текущий режим.

Repr координатора:
    - repr содержит strict=True/False.
"""

import pytest

from action_machine.aspects.aspect_gate_host import AspectGateHost
from action_machine.checkers.checker_gate_host import CheckerGateHost
from action_machine.core.gate_coordinator import GateCoordinator
from action_machine.core.meta_gate_hosts import ActionMetaGateHost, ResourceMetaGateHost
from action_machine.domain.base_domain import BaseDomain

# ─────────────────────────────────────────────────────────────────────────────
# Вспомогательные домены
# ─────────────────────────────────────────────────────────────────────────────


class OrdersDomain(BaseDomain):
    name = "orders"


class CrmDomain(BaseDomain):
    name = "crm"


class WarehouseDomain(BaseDomain):
    name = "warehouse"


# ─────────────────────────────────────────────────────────────────────────────
# Вспомогательные функции для создания тестовых классов
# ─────────────────────────────────────────────────────────────────────────────


def _make_action_with_meta(
    name: str,
    description: str,
    domain: type[BaseDomain] | None = None,
) -> type:
    """
    Создаёт тестовый класс действия с @meta и минимальным summary-аспектом.

    Класс наследует ActionMetaGateHost, AspectGateHost и CheckerGateHost,
    что является минимальным набором для прохождения MetadataBuilder.build().
    """
    attrs: dict = {}

    async def summary(self, params, state, box, connections):
        pass
    summary._new_aspect_meta = {"type": "summary", "description": "test"}
    attrs["summary"] = summary

    cls = type(name, (ActionMetaGateHost, AspectGateHost, CheckerGateHost), attrs)

    cls._meta_info = {
        "description": description,
        "domain": domain,
    }

    return cls


def _make_resource_with_meta(
    name: str,
    description: str,
    domain: type[BaseDomain] | None = None,
) -> type:
    """
    Создаёт тестовый класс ресурсного менеджера с @meta.

    Класс наследует ResourceMetaGateHost, что является минимальным
    набором для прохождения MetadataBuilder.build().
    """
    cls = type(name, (ResourceMetaGateHost,), {})

    cls._meta_info = {
        "description": description,
        "domain": domain,
    }

    return cls


def _make_action_without_meta(name: str) -> type:
    """
    Создаёт тестовый класс действия БЕЗ @meta (для тестов strict
    с промежуточными классами без аспектов).
    """
    return type(name, (ActionMetaGateHost,), {})


# ─────────────────────────────────────────────────────────────────────────────
# Граф: доменные узлы и рёбра belongs_to
# ─────────────────────────────────────────────────────────────────────────────


class TestGraphDomainNodes:
    """Тесты создания доменных узлов и рёбер belongs_to в графе."""

    def test_action_with_domain_creates_domain_node(self):
        """Action с domain → узел "domain" создаётся в графе."""
        coordinator = GateCoordinator()
        cls = _make_action_with_meta("OrderAction", "Создание заказа", OrdersDomain)
        coordinator.get(cls)

        domains = coordinator.get_nodes_by_type("domain")
        assert len(domains) == 1
        assert domains[0]["name"] == "orders"
        assert domains[0]["class_ref"] is OrdersDomain

    def test_two_actions_same_domain_one_node(self):
        """Два Action в одном домене → один узел "domain"."""
        coordinator = GateCoordinator()
        cls1 = _make_action_with_meta("CreateOrder", "Создание", OrdersDomain)
        cls2 = _make_action_with_meta("CancelOrder", "Отмена", OrdersDomain)
        coordinator.get(cls1)
        coordinator.get(cls2)

        domains = coordinator.get_nodes_by_type("domain")
        assert len(domains) == 1
        assert domains[0]["name"] == "orders"

    def test_two_actions_different_domains_two_nodes(self):
        """Два Action в разных доменах → два узла "domain"."""
        coordinator = GateCoordinator()
        cls1 = _make_action_with_meta("OrderAction", "Заказы", OrdersDomain)
        cls2 = _make_action_with_meta("LeadAction", "Лиды", CrmDomain)
        coordinator.get(cls1)
        coordinator.get(cls2)

        domains = coordinator.get_nodes_by_type("domain")
        assert len(domains) == 2
        domain_names = {d["name"] for d in domains}
        assert domain_names == {"orders", "crm"}

    def test_action_without_domain_no_domain_node(self):
        """Action без domain → узел "domain" не создаётся."""
        coordinator = GateCoordinator()
        cls = _make_action_with_meta("PingAction", "Пинг")
        coordinator.get(cls)

        domains = coordinator.get_nodes_by_type("domain")
        assert len(domains) == 0

    def test_resource_with_domain_creates_domain_node(self):
        """ResourceManager с domain → узел "domain" создаётся."""
        coordinator = GateCoordinator()
        cls = _make_resource_with_meta("DbManager", "PostgreSQL", WarehouseDomain)
        coordinator.get(cls)

        domains = coordinator.get_nodes_by_type("domain")
        assert len(domains) == 1
        assert domains[0]["name"] == "warehouse"

    def test_belongs_to_edge_in_tree(self):
        """Дерево зависимостей содержит ребро belongs_to к домену."""
        coordinator = GateCoordinator()
        cls = _make_action_with_meta("OrderAction", "Создание заказа", OrdersDomain)
        coordinator.get(cls)

        metadata = coordinator.get(cls)
        node_key = f"action:{metadata.class_name}"
        tree = coordinator.get_dependency_tree(node_key)

        belongs_to_children = [
            c for c in tree["children"]
            if c.get("edge_type") == "belongs_to"
        ]
        assert len(belongs_to_children) == 1
        assert belongs_to_children[0]["node_type"] == "domain"
        assert belongs_to_children[0]["name"] == "orders"

    def test_action_and_resource_same_domain_shared_node(self):
        """Action и ResourceManager в одном домене → один узел domain."""
        coordinator = GateCoordinator()
        action_cls = _make_action_with_meta("OrderAction", "Заказ", OrdersDomain)
        resource_cls = _make_resource_with_meta("OrderDb", "БД заказов", OrdersDomain)
        coordinator.get(action_cls)
        coordinator.get(resource_cls)

        domains = coordinator.get_nodes_by_type("domain")
        assert len(domains) == 1
        assert domains[0]["name"] == "orders"


# ─────────────────────────────────────────────────────────────────────────────
# Граф: описание в payload
# ─────────────────────────────────────────────────────────────────────────────


class TestGraphDescriptionInPayload:
    """Тесты наличия description и domain в payload узлов графа."""

    def test_action_node_contains_description(self):
        """Payload узла action содержит description из @meta."""
        coordinator = GateCoordinator()
        cls = _make_action_with_meta("OrderAction", "Создание заказа", OrdersDomain)
        coordinator.get(cls)

        actions = coordinator.get_nodes_by_type("action")
        assert len(actions) == 1
        assert actions[0]["meta"]["description"] == "Создание заказа"
        assert actions[0]["meta"]["domain"] == "orders"

    def test_action_node_without_domain(self):
        """Payload узла action без domain содержит domain=None."""
        coordinator = GateCoordinator()
        cls = _make_action_with_meta("PingAction", "Пинг")
        coordinator.get(cls)

        actions = coordinator.get_nodes_by_type("action")
        assert len(actions) == 1
        assert actions[0]["meta"]["description"] == "Пинг"
        assert actions[0]["meta"]["domain"] is None

    def test_dependency_node_contains_description(self):
        """Payload узла dependency (ResourceManager) содержит description."""
        coordinator = GateCoordinator()
        cls = _make_resource_with_meta("RedisManager", "Менеджер Redis", CrmDomain)
        coordinator.get(cls)

        # ResourceManager без аспектов попадает как dependency
        deps = coordinator.get_nodes_by_type("dependency")
        redis_deps = [d for d in deps if "RedisManager" in d["name"]]
        assert len(redis_deps) == 1
        assert redis_deps[0]["meta"]["description"] == "Менеджер Redis"
        assert redis_deps[0]["meta"]["domain"] == "crm"

    def test_plain_class_empty_description(self):
        """Обычный класс без @meta → description пустая строка в payload."""
        coordinator = GateCoordinator()
        cls = type("PlainService", (), {})
        coordinator.get(cls)

        deps = coordinator.get_nodes_by_type("dependency")
        plain_deps = [d for d in deps if "PlainService" in d["name"]]
        assert len(plain_deps) == 1
        assert plain_deps[0]["meta"]["description"] == ""
        assert plain_deps[0]["meta"]["domain"] is None


# ─────────────────────────────────────────────────────────────────────────────
# Strict-режим
# ─────────────────────────────────────────────────────────────────────────────


class TestStrictMode:
    """Тесты strict-режима GateCoordinator."""

    def test_strict_property(self):
        """Свойство strict возвращает текущий режим."""
        assert GateCoordinator(strict=False).strict is False
        assert GateCoordinator(strict=True).strict is True

    def test_strict_default_is_false(self):
        """По умолчанию strict=False."""
        assert GateCoordinator().strict is False

    def test_strict_action_with_domain_ok(self):
        """strict=True, Action с domain → OK."""
        coordinator = GateCoordinator(strict=True)
        cls = _make_action_with_meta("OrderAction", "Заказ", OrdersDomain)
        metadata = coordinator.get(cls)
        assert metadata.meta is not None
        assert metadata.meta.domain is OrdersDomain

    def test_strict_action_without_domain_raises(self):
        """strict=True, Action без domain → ValueError."""
        coordinator = GateCoordinator(strict=True)
        cls = _make_action_with_meta("PingAction", "Пинг")

        with pytest.raises(ValueError, match="strict режим.*не привязан к домену"):
            coordinator.get(cls)

    def test_strict_resource_with_domain_ok(self):
        """strict=True, ResourceManager с domain → OK."""
        coordinator = GateCoordinator(strict=True)
        cls = _make_resource_with_meta("DbManager", "PostgreSQL", WarehouseDomain)
        metadata = coordinator.get(cls)
        assert metadata.meta is not None
        assert metadata.meta.domain is WarehouseDomain

    def test_strict_resource_without_domain_raises(self):
        """strict=True, ResourceManager без domain → ValueError."""
        coordinator = GateCoordinator(strict=True)
        cls = _make_resource_with_meta("BadManager", "Менеджер")

        with pytest.raises(ValueError, match="strict режим.*не привязан к домену"):
            coordinator.get(cls)

    def test_non_strict_action_without_domain_ok(self):
        """strict=False, Action без domain → OK (нет ошибки)."""
        coordinator = GateCoordinator(strict=False)
        cls = _make_action_with_meta("PingAction", "Пинг")
        metadata = coordinator.get(cls)
        assert metadata.meta is not None
        assert metadata.meta.domain is None

    def test_non_strict_resource_without_domain_ok(self):
        """strict=False, ResourceManager без domain → OK."""
        coordinator = GateCoordinator(strict=False)
        cls = _make_resource_with_meta("SimpleManager", "Простой менеджер")
        metadata = coordinator.get(cls)
        assert metadata.meta is not None
        assert metadata.meta.domain is None

    def test_strict_plain_class_no_effect(self):
        """Обычный класс без гейт-хоста → strict не влияет."""
        coordinator = GateCoordinator(strict=True)
        cls = type("PlainService", (), {})
        metadata = coordinator.get(cls)
        assert metadata.meta is None

    def test_strict_action_without_aspects_no_effect(self):
        """Action без аспектов (промежуточный класс) → strict не проверяет domain."""
        coordinator = GateCoordinator(strict=True)
        cls = _make_action_without_meta("IntermediateAction")
        metadata = coordinator.get(cls)
        assert metadata.meta is None


# ─────────────────────────────────────────────────────────────────────────────
# Repr координатора
# ─────────────────────────────────────────────────────────────────────────────


class TestCoordinatorRepr:
    """Тесты repr координатора с учётом strict."""

    def test_empty_repr_contains_strict(self):
        """Пустой координатор: repr содержит strict."""
        assert "strict=False" in repr(GateCoordinator())
        assert "strict=True" in repr(GateCoordinator(strict=True))

    def test_non_empty_repr_contains_strict(self):
        """Непустой координатор: repr содержит strict и классы."""
        coordinator = GateCoordinator(strict=False)
        cls = _make_action_with_meta("TestAction", "Тест")
        coordinator.get(cls)
        r = repr(coordinator)
        assert "strict=False" in r
        assert "TestAction" in r
        assert "nodes=" in r
        assert "edges=" in r
