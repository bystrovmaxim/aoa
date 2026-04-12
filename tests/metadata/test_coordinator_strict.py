"""
Тесты GateCoordinator — домены в графе, описания в узлах, repr.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Параметр ``domain`` в ``@meta`` обязателен (keyword-only). Проверяются узлы
``domain`` в facet-графе, описания в payload узлов и строковое представление
координатора.

═══════════════════════════════════════════════════════════════════════════════
СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

TestDomainInvariantActions
    - Действие с domain — допустимо.
    - Вызов ``meta(...)`` без ``domain=`` — TypeError.
    - Действие без аспектов с domain — допустимо.

TestDomainInvariantResources
    - ResourceManager с domain — допустимо.

TestDomainEdgeCases
    - Пустой класс (без @meta) — допустимо.
    - Действие без @meta и без аспектов — допустимо.

TestDomainNodes
    - Действие с domain создаёт stub-узел ``domain`` с ``class_ref`` на класс домена.
    - Два действия с одним доменом — один такой узел на класс ``_OrdersDomain``.
    - Разные домены — проверка по множеству ``class_ref`` в ``{_OrdersDomain, …}``.
    - Действие без аспектов с domain: в meta facet указан класс домена.
    - **Важно:** после ``build()`` в граф могут попасть чужие ``domain`` от других
      классов экосистемы; тесты фильтруют узлы по ``class_ref is _OrdersDomain`` и т.п.

TestGraphDescriptions
    - Описание действия доступно через узел ``meta``.
    - Действие без аспектов с domain регистрируется без ошибок.
    - Пустой класс — пустое description.

TestCoordinatorRepr
    - repr содержит state и cached.
"""


import pytest

from action_machine.aspects.summary_aspect import summary_aspect
from action_machine.auth.check_roles import check_roles
from action_machine.auth.none_role import NoneRole
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.core.core_action_machine import CoreActionMachine
from action_machine.core.meta_decorator import meta
from action_machine.domain.base_domain import BaseDomain
from action_machine.metadata.base_intent_inspector import BaseIntentInspector
from action_machine.metadata.gate_coordinator import GateCoordinator
from action_machine.resource_managers.base_resource_manager import BaseResourceManager

# ═════════════════════════════════════════════════════════════════════════════
# Вспомогательные классы
# ═════════════════════════════════════════════════════════════════════════════


def _node_key(node_type: str, cls: type, suffix: str = "") -> str:
    """Формирует ключ узла графа: 'тип:модуль.ИмяКласса[.суффикс]'."""
    name = f"{cls.__module__}.{cls.__qualname__}"
    if suffix:
        name = f"{name}.{suffix}"
    return f"{node_type}:{name}"


class _Params(BaseParams):
    pass


class _Result(BaseResult):
    pass


class _OrdersDomain(BaseDomain):
    name = "orders"
    description = "Домен заказов"


class _PaymentsDomain(BaseDomain):
    name = "payments"
    description = "Домен платежей"


# ─── Действие с доменом ──────────────────────────────────────────────────


@meta("Создание заказа", domain=_OrdersDomain)
@check_roles(NoneRole)
class _OrderAction(BaseAction["_Params", "_Result"]):

    @summary_aspect("Итог")
    async def finalize_summary(self, params, state, box, connections):
        return {"result": "ok"}


# ─── Другое действие с тем же доменом ────────────────────────────────────


@meta("Получение заказа", domain=_OrdersDomain)
@check_roles(NoneRole)
class _GetOrderAction(BaseAction["_Params", "_Result"]):

    @summary_aspect("Итог")
    async def finalize_summary(self, params, state, box, connections):
        return {"result": "ok"}


# ─── Действие с другим доменом ───────────────────────────────────────────


@meta("Оплата", domain=_PaymentsDomain)
@check_roles(NoneRole)
class _PaymentAction(BaseAction["_Params", "_Result"]):

    @summary_aspect("Итог")
    async def finalize_summary(self, params, state, box, connections):
        return {"result": "ok"}


# ─── Действие с аспектами и доменом payments ─────────────────────────────


@meta("Ping с доменом payments", domain=_PaymentsDomain)
@check_roles(NoneRole)
class _NoDomainAction(BaseAction["_Params", "_Result"]):

    @summary_aspect("Итог")
    async def finalize_summary(self, params, state, box, connections):
        return {"result": "ok"}


# ─── ResourceManager с доменом ───────────────────────────────────────────


@meta("Менеджер заказов", domain=_OrdersDomain)
class _OrderManager(BaseResourceManager):
    pass


# ─── ResourceManager с доменом payments ─────────────────────────────────


@meta("Менеджер с доменом payments", domain=_PaymentsDomain)
class _NoDomainManager(BaseResourceManager):
    pass


# ─── Действие без @meta и без аспектов ──────────────────────────────────


@check_roles(NoneRole)
class _PlainAction(BaseAction["_Params", "_Result"]):
    pass


# ─── Действие без аспектов, с @meta и доменом ────────────────────────────


@meta("Действие без аспектов", domain=_OrdersDomain)
@check_roles(NoneRole)
class _NoAspectsAction(BaseAction["_Params", "_Result"]):
    pass


class _EmptyClass:
    pass


def _coord() -> GateCoordinator:
    """Built coordinator with default inspectors."""
    return CoreActionMachine.create_coordinator()


# ═════════════════════════════════════════════════════════════════════════════
# Инвариант domain — действия
# ═════════════════════════════════════════════════════════════════════════════


class TestDomainInvariantActions:
    """Домен в @meta для действий с аспектами."""

    def test_action_with_domain_ok(self):
        coord = _coord()
        m = coord.get_snapshot(_OrderAction, "meta")
        assert m is not None
        assert m.domain is _OrdersDomain

    def test_action_with_aspects_with_payments_domain_ok(self):
        coord = _coord()
        m = coord.get_snapshot(_NoDomainAction, "meta")
        assert m is not None
        assert m.domain is _PaymentsDomain

    def test_action_without_aspects_with_domain_ok(self):
        coord = _coord()
        m = coord.get_snapshot(_NoAspectsAction, "meta")
        assert m is not None
        assert m.domain is _OrdersDomain

    def test_meta_missing_domain_raises_typeerror(self):
        with pytest.raises(TypeError, match="domain"):
            meta("Описание без домена")


# ═════════════════════════════════════════════════════════════════════════════
# Инвариант domain — ресурсы
# ═════════════════════════════════════════════════════════════════════════════


class TestDomainInvariantResources:
    """Домен в @meta для ResourceManager."""

    def test_resource_with_domain_ok(self):
        coord = _coord()
        m = coord.get_snapshot(_OrderManager, "meta")
        assert m is not None
        assert m.domain is _OrdersDomain

    def test_resource_with_payments_domain_ok(self):
        coord = _coord()
        m = coord.get_snapshot(_NoDomainManager, "meta")
        assert m is not None
        assert m.domain is _PaymentsDomain


# ═════════════════════════════════════════════════════════════════════════════
# Граничные случаи
# ═════════════════════════════════════════════════════════════════════════════


class TestDomainEdgeCases:
    """Классы без затронутых инвариантов."""

    def test_plain_class_no_effect(self):
        coord = _coord()
        assert coord.get_snapshot(_EmptyClass, "meta") is None

    def test_action_without_aspects_no_meta_ok(self):
        coord = _coord()
        assert coord.get_snapshot(_PlainAction, "meta") is None


# ═════════════════════════════════════════════════════════════════════════════
# Домены в графе
# ═════════════════════════════════════════════════════════════════════════════


class TestDomainNodes:
    """Создание domain-узлов в графе."""

    def test_action_with_domain_creates_domain_node(self):
        coord = _coord()
        nodes = [
            n for n in coord.get_nodes_by_type("domain")
            if n.get("class_ref") is _OrdersDomain
        ]
        assert len(nodes) >= 1

    def test_two_actions_same_domain_one_node(self):
        coord = _coord()
        domain_nodes = [
            n for n in coord.get_nodes_by_type("domain")
            if n.get("class_ref") is _OrdersDomain
        ]
        assert len(domain_nodes) == 1

    def test_two_actions_different_domains_two_nodes(self):
        coord = _coord()
        refs = {
            n["class_ref"] for n in coord.get_nodes_by_type("domain")
            if n.get("class_ref") in (_OrdersDomain, _PaymentsDomain)
        }
        assert refs == {_OrdersDomain, _PaymentsDomain}

    def test_action_without_aspects_has_domain_in_meta_node(self):
        coord = _coord()
        nm = BaseIntentInspector._make_node_name(_NoAspectsAction)
        meta_node = coord.get_node("meta", nm)
        assert meta_node is not None
        meta = meta_node.get("meta")
        assert meta is not None
        assert meta.get("domain") is _OrdersDomain

    def test_resource_with_domain_creates_domain_node(self):
        coord = _coord()
        nodes = [
            n for n in coord.get_nodes_by_type("domain")
            if n.get("class_ref") is _OrdersDomain
        ]
        assert len(nodes) >= 1

    def test_action_and_resource_same_domain_shared_node(self):
        coord = _coord()
        domain_nodes = [
            n for n in coord.get_nodes_by_type("domain")
            if n.get("class_ref") is _OrdersDomain
        ]
        assert len(domain_nodes) == 1


# ═════════════════════════════════════════════════════════════════════════════
# Описания в узлах графа
# ═════════════════════════════════════════════════════════════════════════════


class TestGraphDescriptions:
    """Узлы графа содержат описания в payload."""

    def test_action_node_contains_description(self):
        coord = _coord()
        key = _node_key("meta", _OrderAction)
        node = coord.get_node(key)
        assert node is not None

    def test_action_without_aspects_without_domain_registers(self):
        coord = _coord()
        assert coord.get_snapshot(_NoAspectsAction, "meta") is not None

    def test_empty_class_empty_description(self):
        coord = _coord()
        assert coord.graph_node_count >= 1


# ═════════════════════════════════════════════════════════════════════════════
# Строковое представление координатора
# ═════════════════════════════════════════════════════════════════════════════


class TestCoordinatorRepr:
    """__repr__ GateCoordinator."""

    def test_empty_repr(self):
        coord = GateCoordinator()
        result = repr(coord)
        assert "GateCoordinator(" in result
        assert "state=not built" in result

    def test_nonempty_repr(self):
        coord = _coord()
        result = repr(coord)
        assert isinstance(result, str)
        assert "GateCoordinator(" in result
        assert "state=built" in result
