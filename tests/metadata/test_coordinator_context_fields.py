# tests/metadata/test_coordinator_context_fields.py
"""
Тесты узлов context_field и рёбер requires_context в графе координатора.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Проверяет, что GateCoordinator корректно создаёт узлы типа "context_field"
и рёбра "requires_context" при регистрации Action с @context_requires
на аспектах и обработчиках ошибок.

Узлы context_field переиспользуются: если два аспекта запрашивают
user.user_id, создаётся один узел и два ребра к нему.

Рёбра requires_context — leaf-рёбра, добавляемые без проверки
ацикличности (через _add_leaf_edge).

═══════════════════════════════════════════════════════════════════════════════
ТЕСТОВЫЕ ACTION
═══════════════════════════════════════════════════════════════════════════════

Тесты в этом файле создают намеренно специфичные Action внутри тестов
(не в tests/domain/), потому что они нужны только для проверки
конкретных сценариев графа:

- Action с одним аспектом и @context_requires.
- Action с двумя аспектами, запрашивающими одно и то же поле.
- Action с обработчиком ошибок и @context_requires.
- Action без @context_requires (для проверки отсутствия рёбер).
"""

from pydantic import Field

from action_machine.aspects.regular_aspect import regular_aspect
from action_machine.aspects.summary_aspect import summary_aspect
from action_machine.auth import ROLE_NONE, check_roles
from action_machine.context.context_requires_decorator import context_requires
from action_machine.context.ctx_constants import Ctx
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.core.base_state import BaseState
from action_machine.core.gate_coordinator import GateCoordinator
from action_machine.core.meta_decorator import meta
from action_machine.core.tools_box import ToolsBox
from action_machine.on_error.on_error_decorator import on_error
from action_machine.resource_managers.base_resource_manager import BaseResourceManager
from tests.domain.domains import SystemDomain

# ═════════════════════════════════════════════════════════════════════════════
# Вспомогательные тестовые компоненты
# ═════════════════════════════════════════════════════════════════════════════


class _CtxTestParams(BaseParams):
    """Параметры для тестовых Action контекстных зависимостей."""
    value: str = Field(description="Тестовое значение")


class _CtxTestResult(BaseResult):
    """Результат для тестовых Action контекстных зависимостей."""
    status: str = Field(description="Статус")


# ═════════════════════════════════════════════════════════════════════════════
# Тестовые Action (edge-case, создаются внутри тестов)
# ═════════════════════════════════════════════════════════════════════════════


@meta(description="Action с одним аспектом и context_requires", domain=SystemDomain)
@check_roles(ROLE_NONE)
class _SingleContextAction(BaseAction[_CtxTestParams, _CtxTestResult]):
    """Один regular-аспект запрашивает user.user_id и request.trace_id."""

    @regular_aspect("Аудит")
    @context_requires(Ctx.User.user_id, Ctx.Request.trace_id)
    async def audit_aspect(
        self, params: _CtxTestParams, state: BaseState,
        box: ToolsBox, connections: dict[str, BaseResourceManager],
        ctx: object,
    ) -> dict:
        return {}

    @summary_aspect("Результат")
    async def result_summary(
        self, params: _CtxTestParams, state: BaseState,
        box: ToolsBox, connections: dict[str, BaseResourceManager],
    ) -> _CtxTestResult:
        return _CtxTestResult(status="ok")


@meta(description="Action с двумя аспектами, запрашивающими одно поле", domain=SystemDomain)
@check_roles(ROLE_NONE)
class _SharedContextFieldAction(BaseAction[_CtxTestParams, _CtxTestResult]):
    """Два regular-аспекта запрашивают user.user_id — узел переиспользуется."""

    @regular_aspect("Первый аспект")
    @context_requires(Ctx.User.user_id)
    async def first_aspect(
        self, params: _CtxTestParams, state: BaseState,
        box: ToolsBox, connections: dict[str, BaseResourceManager],
        ctx: object,
    ) -> dict:
        return {}

    @regular_aspect("Второй аспект")
    @context_requires(Ctx.User.user_id, Ctx.User.roles)
    async def second_aspect(
        self, params: _CtxTestParams, state: BaseState,
        box: ToolsBox, connections: dict[str, BaseResourceManager],
        ctx: object,
    ) -> dict:
        return {}

    @summary_aspect("Результат")
    async def result_summary(
        self, params: _CtxTestParams, state: BaseState,
        box: ToolsBox, connections: dict[str, BaseResourceManager],
    ) -> _CtxTestResult:
        return _CtxTestResult(status="ok")


@meta(description="Action с on_error и context_requires", domain=SystemDomain)
@check_roles(ROLE_NONE)
class _ErrorHandlerContextAction(BaseAction[_CtxTestParams, _CtxTestResult]):
    """Обработчик ошибок запрашивает контекстные поля."""

    @regular_aspect("Операция")
    async def operation_aspect(
        self, params: _CtxTestParams, state: BaseState,
        box: ToolsBox, connections: dict[str, BaseResourceManager],
    ) -> dict:
        return {}

    @summary_aspect("Результат")
    async def result_summary(
        self, params: _CtxTestParams, state: BaseState,
        box: ToolsBox, connections: dict[str, BaseResourceManager],
    ) -> _CtxTestResult:
        return _CtxTestResult(status="ok")

    @on_error(ValueError, description="Обработка с контекстом")
    @context_requires(Ctx.User.user_id, Ctx.Request.client_ip)
    async def handle_value_on_error(
        self, params: _CtxTestParams, state: BaseState,
        box: ToolsBox, connections: dict[str, BaseResourceManager],
        error: Exception, ctx: object,
    ) -> _CtxTestResult:
        return _CtxTestResult(status="error_handled")


@meta(description="Action без context_requires", domain=SystemDomain)
@check_roles(ROLE_NONE)
class _NoContextAction(BaseAction[_CtxTestParams, _CtxTestResult]):
    """Все аспекты без @context_requires — рёбер requires_context не будет."""

    @regular_aspect("Простой аспект")
    async def simple_aspect(
        self, params: _CtxTestParams, state: BaseState,
        box: ToolsBox, connections: dict[str, BaseResourceManager],
    ) -> dict:
        return {}

    @summary_aspect("Результат")
    async def result_summary(
        self, params: _CtxTestParams, state: BaseState,
        box: ToolsBox, connections: dict[str, BaseResourceManager],
    ) -> _CtxTestResult:
        return _CtxTestResult(status="ok")


# ═════════════════════════════════════════════════════════════════════════════
# Тесты: узлы context_field
# ═════════════════════════════════════════════════════════════════════════════


class TestContextFieldNodes:
    """Тесты создания узлов context_field в графе координатора."""

    def test_context_fields_created_for_aspect(self) -> None:
        """Регистрация Action с @context_requires создаёт узлы context_field."""
        # Arrange
        coordinator = GateCoordinator()

        # Act — регистрация Action с аспектом, запрашивающим два поля
        coordinator.get(_SingleContextAction)

        # Assert — узлы context_field созданы
        ctx_nodes = coordinator.get_nodes_by_type("context_field")
        ctx_names = {n["name"] for n in ctx_nodes}
        assert "user.user_id" in ctx_names
        assert "request.trace_id" in ctx_names

    def test_context_field_node_has_path_meta(self) -> None:
        """Узел context_field содержит meta.path с dot-path ключом."""
        # Arrange
        coordinator = GateCoordinator()

        # Act
        coordinator.get(_SingleContextAction)

        # Assert — payload узла содержит path
        node = coordinator.get_node("context_field:user.user_id")
        assert node is not None
        assert node["meta"]["path"] == "user.user_id"

    def test_context_field_reused_across_aspects(self) -> None:
        """Один узел context_field переиспользуется несколькими аспектами."""
        # Arrange
        coordinator = GateCoordinator()

        # Act — два аспекта запрашивают user.user_id
        coordinator.get(_SharedContextFieldAction)

        # Assert — узел user.user_id один, но два ребра к нему
        ctx_nodes = coordinator.get_nodes_by_type("context_field")
        user_id_nodes = [n for n in ctx_nodes if n["name"] == "user.user_id"]
        assert len(user_id_nodes) == 1

    def test_no_context_fields_without_decorator(self) -> None:
        """Action без @context_requires не создаёт узлов context_field."""
        # Arrange
        coordinator = GateCoordinator()

        # Act
        coordinator.get(_NoContextAction)

        # Assert — нет узлов context_field
        ctx_nodes = coordinator.get_nodes_by_type("context_field")
        assert len(ctx_nodes) == 0

    def test_context_fields_for_error_handler(self) -> None:
        """@context_requires на обработчике ошибок создаёт узлы context_field."""
        # Arrange
        coordinator = GateCoordinator()

        # Act
        coordinator.get(_ErrorHandlerContextAction)

        # Assert — поля из обработчика ошибок в графе
        ctx_nodes = coordinator.get_nodes_by_type("context_field")
        ctx_names = {n["name"] for n in ctx_nodes}
        assert "user.user_id" in ctx_names
        assert "request.client_ip" in ctx_names


# ═════════════════════════════════════════════════════════════════════════════
# Тесты: рёбра requires_context
# ═════════════════════════════════════════════════════════════════════════════


class TestRequiresContextEdges:
    """Тесты рёбер requires_context от аспектов/обработчиков к полям контекста."""

    def test_edges_from_aspect_to_context_fields(self) -> None:
        """Аспект с @context_requires имеет рёбра requires_context к полям."""
        # Arrange
        coordinator = GateCoordinator()
        coordinator.get(_SingleContextAction)
        class_name = coordinator.get(_SingleContextAction).class_name

        # Act — получаем потомков узла аспекта
        aspect_key = f"aspect:{class_name}.audit_aspect"
        children = coordinator.get_children(aspect_key)

        # Assert — два потомка (user.user_id, request.trace_id)
        child_names = {c["name"] for c in children}
        assert "user.user_id" in child_names
        assert "request.trace_id" in child_names

    def test_shared_field_has_multiple_incoming_edges(self) -> None:
        """Один context_field может иметь рёбра от нескольких аспектов."""
        # Arrange
        coordinator = GateCoordinator()
        coordinator.get(_SharedContextFieldAction)

        # Act — проверяем граф: user.user_id должен быть потомком обоих аспектов
        class_name = coordinator.get(_SharedContextFieldAction).class_name
        first_key = f"aspect:{class_name}.first_aspect"
        second_key = f"aspect:{class_name}.second_aspect"

        first_children = {c["name"] for c in coordinator.get_children(first_key)}
        second_children = {c["name"] for c in coordinator.get_children(second_key)}

        # Assert — оба аспекта ведут к user.user_id
        assert "user.user_id" in first_children
        assert "user.user_id" in second_children

        # Assert — второй аспект дополнительно ведёт к user.roles
        assert "user.roles" in second_children
        assert "user.roles" not in first_children

    def test_edges_from_error_handler_to_context_fields(self) -> None:
        """Обработчик ошибок с @context_requires имеет рёбра requires_context."""
        # Arrange
        coordinator = GateCoordinator()
        coordinator.get(_ErrorHandlerContextAction)
        class_name = coordinator.get(_ErrorHandlerContextAction).class_name

        # Act — потомки узла обработчика ошибок
        handler_key = f"error_handler:{class_name}.handle_value_on_error"
        children = coordinator.get_children(handler_key)

        # Assert — два контекстных поля
        child_names = {c["name"] for c in children}
        assert "user.user_id" in child_names
        assert "request.client_ip" in child_names

    def test_no_edges_without_context_requires(self) -> None:
        """Аспекты без @context_requires не имеют рёбер requires_context."""
        # Arrange
        coordinator = GateCoordinator()
        coordinator.get(_NoContextAction)
        class_name = coordinator.get(_NoContextAction).class_name

        # Act — потомки аспекта
        aspect_key = f"aspect:{class_name}.simple_aspect"
        children = coordinator.get_children(aspect_key)

        # Assert — нет потомков типа context_field
        ctx_children = [c for c in children if c["node_type"] == "context_field"]
        assert len(ctx_children) == 0

    def test_requires_context_in_dependency_tree(self) -> None:
        """Рёбра requires_context видны в get_dependency_tree()."""
        # Arrange
        coordinator = GateCoordinator()
        coordinator.get(_SingleContextAction)
        class_name = coordinator.get(_SingleContextAction).class_name

        # Act — полное дерево от Action
        action_key = f"action:{class_name}"
        tree = coordinator.get_dependency_tree(action_key)

        # Assert — где-то в дереве есть edge_type "requires_context"
        def find_edge_types(node: dict) -> set:
            types = set()
            for child in node.get("children", []):
                edge_type = child.get("edge_type")
                if edge_type:
                    types.add(edge_type)
                types |= find_edge_types(child)
            return types

        all_edge_types = find_edge_types(tree)
        assert "requires_context" in all_edge_types


# ═════════════════════════════════════════════════════════════════════════════
# Тесты: интеграция с invalidate и rebuild
# ═════════════════════════════════════════════════════════════════════════════


class TestContextFieldsAfterInvalidate:
    """Тесты корректности узлов context_field после инвалидации кеша."""

    def test_invalidate_rebuilds_context_fields(self) -> None:
        """После invalidate и повторной регистрации узлы пересоздаются."""
        # Arrange
        coordinator = GateCoordinator()
        coordinator.get(_SingleContextAction)

        # Act — инвалидируем и перестраиваем
        coordinator.invalidate(_SingleContextAction)
        coordinator.get(_SingleContextAction)

        # Assert — узлы context_field на месте
        ctx_nodes = coordinator.get_nodes_by_type("context_field")
        ctx_names = {n["name"] for n in ctx_nodes}
        assert "user.user_id" in ctx_names
        assert "request.trace_id" in ctx_names

    def test_invalidate_all_clears_context_fields(self) -> None:
        """invalidate_all() очищает все узлы, включая context_field."""
        # Arrange
        coordinator = GateCoordinator()
        coordinator.get(_SingleContextAction)
        assert coordinator.graph_node_count > 0

        # Act
        coordinator.invalidate_all()

        # Assert — граф полностью пуст
        assert coordinator.graph_node_count == 0
        ctx_nodes = coordinator.get_nodes_by_type("context_field")
        assert len(ctx_nodes) == 0
