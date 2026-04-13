# tests/compensate/test_compensate_graph.py
"""
Интеграция компенсаторов (@compensate) с фасетным графом GateCoordinator.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Проверяет, как ``CompensateIntentInspector`` вписывается в единую модель
фасетов: **один** узел ``compensator`` на класс ``BaseAction``, независимо от
числа методов отката. Имя узла — ``module.QualName`` **класса действия**, а не
имени метода; детализация по каждому компенсатору — в ``meta.compensators`` как
кортеж записей — каждая запись ``tuple[tuple[str, Any], ...]`` (пары ключ/значение,
как ``_make_meta``): ``method_name``, ``target_aspect_name``, ``description``,
``method_ref``, ``context_keys``.

═══════════════════════════════════════════════════════════════════════════════
АРХИТЕКТУРНОЕ РЕШЕНИЕ (почему нет has_compensator в дереве)
═══════════════════════════════════════════════════════════════════════════════

В старой визуализации координатора между узлом ``action`` и ``compensator``
рисовалось ребро ``has_compensator``, а контекстные требования — отдельными
рёбрами к ``context_field``. В фасетной сборке **рёбра из payload компенсатора
пусты** (``edges=()``): связь «этот класс содержит компенсаторы» выражается
фактом наличия узла с тем же ``class_ref``, а ``@context_requires`` на методе
отката отражается **внутри** поля ``context_keys`` записи, без отдельного подграфа
контекста. Это упрощает коммит графа и устраняет дублирование с runtime metadata,
где те же данные уже есть для машины саги.

═══════════════════════════════════════════════════════════════════════════════
СТРУКТУРНЫЙ УЗЕЛ action И ТЕСТЫ
═══════════════════════════════════════════════════════════════════════════════

Инспекторы для ``@depends`` и ``@connection`` порождают один узел ``action``
(после слияния в координаторе), но только при наличии этих деклараций.
Тестовые действия в этом файле **без**
зависимостей и соединений поэтому **не** создают structural ``action``; вместо
«ребро action→compensator» проверяется согласованность ``meta`` и ``compensator``
для одного ``class_ref``, а также набор типов фасетов через
``get_nodes_for_class``.

═══════════════════════════════════════════════════════════════════════════════
СТРУКТУРА КЛАССОВ ТЕСТОВ
═══════════════════════════════════════════════════════════════════════════════

TestCompensatorGraphNodes — корректность одного узла ``compensator`` и полей
    ``meta.compensators``; фильтрация по ``class_ref`` (граф глобальный).

TestCompensatorGraphEdges — согласованность facet ``meta`` и ``compensator``;
    контекст на откате с ``@context_requires`` vs пустой frozenset.

TestCompensatorInDependencyTree — историческое имя класса; фактически проверка
    множества ``node_type`` у ``get_nodes_for_class`` (facets класса).
"""

from __future__ import annotations

from action_machine.graph.gate_coordinator import GateCoordinator
from action_machine.intents.aspects.regular_aspect_decorator import regular_aspect
from action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from action_machine.intents.auth import NoneRole, check_roles
from action_machine.intents.compensate import compensate
from action_machine.intents.context import Ctx, context_requires
from action_machine.intents.meta.meta_decorator import meta
from action_machine.model.base_action import BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from action_machine.runtime.machines.core_action_machine import CoreActionMachine
from tests.scenarios.domain_model.domains import TestDomain

# ═════════════════════════════════════════════════════════════════════════════
# Вспомогательные функции и классы
# ═════════════════════════════════════════════════════════════════════════════


def _compensator_nodes_for(coordinator: GateCoordinator, action_cls: type) -> list[dict]:
    """
    Возвращает узлы ``compensator``, порождённые конкретным классом действия.

    Обязательно: глобальный ``get_nodes_by_type`` после ``build()`` включает
    компенсаторы **других** тестовых модулей (например scenarios.domain_model), без
    фильтра по ``class_ref`` неверны и счётчики, и выбор ``nodes[0]``.
    """
    return [
        n for n in coordinator.get_nodes_by_type("compensator")
        if n.get("class_ref") is action_cls
    ]


def _coordinator() -> GateCoordinator:
    """Return built coordinator with default inspectors."""
    return CoreActionMachine.create_coordinator()


class EmptyParams(BaseParams):
    pass


class EmptyResult(BaseResult):
    pass


@meta(description="Тестовое действие с компенсатором", domain=TestDomain)
@check_roles(NoneRole)
class ActionWithCompensatorAction(BaseAction[EmptyParams, EmptyResult]):

    @regular_aspect("Аспект")
    async def target_aspect(self, params, state, box, connections):
        return {}

    @compensate("target_aspect", "Тестовый компенсатор")
    async def rollback_compensate(self, params, state_before, state_after,
                                  box, connections, error):
        pass

    @summary_aspect("Саммари")
    async def summary(self, params, state, box, connections):
        return EmptyResult()


@meta(description="Тестовое действие с компенсатором и контекстом", domain=TestDomain)
@check_roles(NoneRole)
class ActionWithContextCompensatorAction(BaseAction[EmptyParams, EmptyResult]):

    @regular_aspect("Аспект")
    async def target_aspect(self, params, state, box, connections):
        return {}

    @compensate("target_aspect", "Компенсатор с контекстом")
    @context_requires(Ctx.User.user_id)
    async def rollback_with_context_compensate(self, params, state_before, state_after,
                                               box, connections, error, ctx):
        pass

    @summary_aspect("Саммари")
    async def summary(self, params, state, box, connections):
        return EmptyResult()


# ═════════════════════════════════════════════════════════════════════════════
# TestCompensatorGraphNodes
# ═════════════════════════════════════════════════════════════════════════════


class TestCompensatorGraphNodes:
    """Узел ``compensator`` и структура ``meta.compensators`` для одного Action-класса."""

    def test_compensator_node_created(self) -> None:
        """
        При регистрации действия с компенсатором появляется facet-узел 'compensator'
        на этот класс с кортежом compensators в meta.
        """
        coordinator = _coordinator()

        nodes = _compensator_nodes_for(coordinator, ActionWithCompensatorAction)
        assert len(nodes) == 1

        node = nodes[0]
        assert node["node_type"] == "compensator"
        assert ActionWithCompensatorAction.__qualname__ in node["name"]
        compensators = dict(node["meta"])["compensators"]
        row = dict(next(c for c in compensators if dict(c)["method_name"] == "rollback_compensate"))
        assert row["target_aspect_name"] == "target_aspect"
        assert row["description"] == "Тестовый компенсатор"

    def test_get_nodes_by_type_returns_all_compensators(self) -> None:
        """
        Для каждого из двух действий — свой узел компенсатора (агрегат).
        """
        coordinator = _coordinator()

        n1 = _compensator_nodes_for(coordinator, ActionWithCompensatorAction)
        n2 = _compensator_nodes_for(coordinator, ActionWithContextCompensatorAction)
        assert len(n1) == 1
        assert len(n2) == 1

        names = [n["name"] for n in (n1 + n2)]
        assert any(ActionWithCompensatorAction.__qualname__ in n for n in names)
        assert any(ActionWithContextCompensatorAction.__qualname__ in n for n in names)

    def test_compensator_node_metadata(self) -> None:
        """
        meta.compensators хранит записи с ключами method_name, target_aspect_name, …
        """
        coordinator = _coordinator()

        nodes = _compensator_nodes_for(coordinator, ActionWithCompensatorAction)
        meta = dict(nodes[0]["meta"])
        rows = meta["compensators"]
        row = dict(next(r for r in rows if dict(r)["method_name"] == "rollback_compensate"))
        assert row["target_aspect_name"] == "target_aspect"
        assert row["description"] == "Тестовый компенсатор"


# ═════════════════════════════════════════════════════════════════════════════
# TestCompensatorGraphEdges
# ═════════════════════════════════════════════════════════════════════════════


class TestCompensatorGraphEdges:
    """
    Согласованность фасетов ``meta`` и ``compensator`` для одного класса.

    Structural ``action`` отсутствует у действий без ``@depends``/``@connection`` —
    это ожидаемо и не является регрессией интеграции компенсаторов.
    """

    def test_has_compensator_edge_exists(self) -> None:
        """Для действия есть facet meta и facet compensator (узел action только при depends/connection)."""
        coordinator = _coordinator()

        meta_nodes = [
            n for n in coordinator.get_nodes_by_type("meta")
            if n.get("class_ref") is ActionWithCompensatorAction
        ]
        assert len(meta_nodes) == 1
        comp_nodes = _compensator_nodes_for(coordinator, ActionWithCompensatorAction)
        assert len(comp_nodes) == 1

    def test_requires_context_edge_for_compensator(self) -> None:
        """
        Ключи @context_requires попадают в meta.compensators (поле context_keys).
        """
        coordinator = _coordinator()

        comp_nodes = _compensator_nodes_for(coordinator, ActionWithContextCompensatorAction)
        assert len(comp_nodes) == 1
        rows: tuple = dict(comp_nodes[0]["meta"])["compensators"]
        row = dict(next(r for r in rows if dict(r)["method_name"] == "rollback_with_context_compensate"))
        assert Ctx.User.user_id in row["context_keys"]

    def test_compensator_without_context_no_requires_context_edge(self) -> None:
        """У компенсатора без @context_requires пустой frozenset контекста."""
        coordinator = _coordinator()

        comp_nodes = _compensator_nodes_for(coordinator, ActionWithCompensatorAction)
        row = dict(
            next(
                r for r in dict(comp_nodes[0]["meta"])["compensators"]
                if dict(r)["method_name"] == "rollback_compensate"
            ),
        )
        assert row["context_keys"] == frozenset()


# ═════════════════════════════════════════════════════════════════════════════
# TestCompensatorInDependencyTree
# ═════════════════════════════════════════════════════════════════════════════


class TestCompensatorInDependencyTree:
    """
    Фасеты, порождённые классом действия (``get_nodes_for_class``).

    Имя класса оставлено от старой формулировки «dependency tree»; проверка не
    вызывает ``get_dependency_tree``, а фиксирует наличие ``compensator`` и
    ``meta`` среди узлов с общим ``class_ref``.
    """

    def test_dependency_tree_includes_compensator(self) -> None:
        """У зарегистрированного action есть facet compensator."""
        coordinator = _coordinator()

        facets = {n["node_type"] for n in coordinator.get_nodes_for_class(ActionWithCompensatorAction)}
        assert "compensator" in facets
        assert "meta" in facets

    def test_dependency_tree_depth_for_compensator_with_context(self) -> None:
        """Компенсатор с контекстом хранит ключи в meta, без отдельных рёбер."""
        coordinator = _coordinator()

        node = _compensator_nodes_for(coordinator, ActionWithContextCompensatorAction)[0]
        row = dict(
            next(
                r for r in dict(node["meta"])["compensators"]
                if dict(r)["method_name"] == "rollback_with_context_compensate"
            ),
        )
        assert Ctx.User.user_id in row["context_keys"]
