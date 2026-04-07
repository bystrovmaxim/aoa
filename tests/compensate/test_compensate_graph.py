# tests/compensate/test_compensate_graph.py
"""
Тесты графа GateCoordinator для компенсаторов.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Проверяет, что GateCoordinator правильно добавляет в граф узлы компенсаторов
и рёбра от действий к компенсаторам, а также рёбра requires_context для
компенсаторов с @context_requires.

═══════════════════════════════════════════════════════════════════════════════
СТРУКТУРА
═══════════════════════════════════════════════════════════════════════════════

TestCompensatorGraphNodes      — узлы типа "compensator"
TestCompensatorGraphEdges      — рёбра "has_compensator" и "requires_context"
TestCompensatorInDependencyTree — дерево зависимостей включает компенсаторы
"""

from __future__ import annotations

from action_machine.aspects.regular_aspect import regular_aspect
from action_machine.aspects.summary_aspect import summary_aspect
from action_machine.auth import ROLE_NONE, check_roles
from action_machine.compensate import compensate
from action_machine.context import Ctx, context_requires
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.core.gate_coordinator import GateCoordinator
from action_machine.core.meta_decorator import meta

# ═════════════════════════════════════════════════════════════════════════════
# Вспомогательные классы
# ═════════════════════════════════════════════════════════════════════════════


class EmptyParams(BaseParams):
    pass


class EmptyResult(BaseResult):
    pass


@meta(description="Тестовое действие с компенсатором")
@check_roles(ROLE_NONE)
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


@meta(description="Тестовое действие с компенсатором и контекстом")
@check_roles(ROLE_NONE)
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
    """Проверяет создание узлов типа 'compensator' в графе."""

    def test_compensator_node_created(self) -> None:
        """
        При регистрации действия с компенсатором в графе появляется узел типа 'compensator'.
        """
        coordinator = GateCoordinator()
        coordinator.get(ActionWithCompensatorAction)

        nodes = coordinator.get_nodes_by_type("compensator")
        assert len(nodes) == 1

        node = nodes[0]
        assert node["node_type"] == "compensator"
        assert node["name"].endswith("rollback_compensate")
        assert "target_aspect" in node["meta"]
        assert node["meta"]["target_aspect"] == "target_aspect"
        assert node["meta"]["description"] == "Тестовый компенсатор"

    def test_get_nodes_by_type_returns_all_compensators(self) -> None:
        """
        get_nodes_by_type("compensator") возвращает все узлы компенсаторов.
        """
        coordinator = GateCoordinator()
        coordinator.get(ActionWithCompensatorAction)
        coordinator.get(ActionWithContextCompensatorAction)

        nodes = coordinator.get_nodes_by_type("compensator")
        assert len(nodes) == 2

        names = [n["name"] for n in nodes]
        assert any("rollback_compensate" in n for n in names)
        assert any("rollback_with_context_compensate" in n for n in names)

    def test_compensator_node_metadata(self) -> None:
        """
        Метаданные узла компенсатора содержат target_aspect, description, method_name.
        """
        coordinator = GateCoordinator()
        coordinator.get(ActionWithCompensatorAction)

        nodes = coordinator.get_nodes_by_type("compensator")
        meta = nodes[0]["meta"]

        assert "target_aspect" in meta
        assert "description" in meta
        assert "method_name" in meta
        assert meta["method_name"] == "rollback_compensate"


# ═════════════════════════════════════════════════════════════════════════════
# TestCompensatorGraphEdges
# ═════════════════════════════════════════════════════════════════════════════


class TestCompensatorGraphEdges:
    """Проверяет рёбра от action к компенсатору и от компенсатора к context_field."""

    def test_has_compensator_edge_exists(self) -> None:
        """
        Ребро "has_compensator" соединяет узел action с узлом compensator.
        """
        coordinator = GateCoordinator()
        coordinator.get(ActionWithCompensatorAction)

        action_nodes = coordinator.get_nodes_by_type("action")
        assert len(action_nodes) == 1
        action_name = action_nodes[0]["name"]

        comp_nodes = coordinator.get_nodes_by_type("compensator")
        comp_name = comp_nodes[0]["name"]

        tree = coordinator.get_dependency_tree(f"action:{action_name}")

        found = False
        for child in tree.get("children", []):
            if child.get("edge_type") == "has_compensator" and child.get("name") == comp_name:
                found = True
                break
        assert found

    def test_requires_context_edge_for_compensator(self) -> None:
        """
        Для компенсатора с @context_requires создаётся ребро "requires_context"
        от компенсатора к узлу context_field.
        """
        coordinator = GateCoordinator()
        coordinator.get(ActionWithContextCompensatorAction)

        comp_nodes = coordinator.get_nodes_by_type("compensator")
        assert len(comp_nodes) == 1
        comp_name = comp_nodes[0]["name"]

        tree = coordinator.get_dependency_tree(f"compensator:{comp_name}")

        found = False
        for child in tree.get("children", []):
            if child.get("edge_type") == "requires_context":
                if "user.user_id" in child.get("name", ""):
                    found = True
                    break
        assert found

    def test_compensator_without_context_no_requires_context_edge(self) -> None:
        """
        Для компенсатора без @context_requires нет ребра requires_context.
        """
        coordinator = GateCoordinator()
        coordinator.get(ActionWithCompensatorAction)

        comp_nodes = coordinator.get_nodes_by_type("compensator")
        comp_name = comp_nodes[0]["name"]

        tree = coordinator.get_dependency_tree(f"compensator:{comp_name}")
        children = tree.get("children", [])
        requires_context_edges = [c for c in children if c.get("edge_type") == "requires_context"]
        assert len(requires_context_edges) == 0


# ═════════════════════════════════════════════════════════════════════════════
# TestCompensatorInDependencyTree
# ═════════════════════════════════════════════════════════════════════════════


class TestCompensatorInDependencyTree:
    """Проверяет, что компенсатор появляется в дереве зависимостей действия."""

    def test_dependency_tree_includes_compensator(self) -> None:
        """
        get_dependency_tree() для action включает компенсатор как дочерний узел.
        """
        coordinator = GateCoordinator()
        coordinator.get(ActionWithCompensatorAction)

        action_nodes = coordinator.get_nodes_by_type("action")
        action_name = action_nodes[0]["name"]

        tree = coordinator.get_dependency_tree(f"action:{action_name}")

        compensator_children = [
            child for child in tree.get("children", [])
            if child.get("node_type") == "compensator"
        ]
        assert len(compensator_children) == 1
        assert compensator_children[0]["edge_type"] == "has_compensator"

    def test_dependency_tree_depth_for_compensator_with_context(self) -> None:
        """
        Дерево зависимостей компенсатора с контекстом включает context_field.
        """
        coordinator = GateCoordinator()
        coordinator.get(ActionWithContextCompensatorAction)

        comp_nodes = coordinator.get_nodes_by_type("compensator")
        comp_name = comp_nodes[0]["name"]

        tree = coordinator.get_dependency_tree(f"compensator:{comp_name}")

        context_children = [
            child for child in tree.get("children", [])
            if child.get("edge_type") == "requires_context"
        ]
        assert len(context_children) >= 1
        assert context_children[0]["node_type"] == "context_field"
