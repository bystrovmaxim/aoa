# tests/metadata/test_coordinator_context_fields.py
"""
Метаданные @context_requires: runtime metadata cache и фасетный граф.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Проверяет, что ключи контекста, объявленные через ``@context_requires``, попадают
в снимки facet’ов так, как их видит рантайм: на regular-аспектах и на
обработчиках ``@on_error``. Координатор после ``build()`` отдаёт их через
``get_snapshot(cls, \"aspect\")`` / ``get_snapshot(cls, \"error_handler\")`` и т.д.

═══════════════════════════════════════════════════════════════════════════════
ЭВОЛЮЦИЯ МОДЕЛИ (почему тесты больше не про «узлы context_field»)
═══════════════════════════════════════════════════════════════════════════════

В ранней модели координатора **отдельные узлы** ``context_field`` и **рёбра**
``requires_context`` визуализировали запрос контекста на графе: два аспекта с
одним и тем же ключом ссылались на один узел поля, reuse был явен на диаграмме.

После перехода на **транзакционное построение графа из FacetPayload** визуальная
детализация «каждое поле контекста = узел» **не дублируется** в том же виде:
контекст остаётся **семантикой шага** — кортеж строковых ключей на ``AspectMeta``,
``OnErrorMeta`` и т.д., а граф описывает фасеты (role, meta, aspect, …) и
структурные рёбра (depends, connection, belongs_to, …). Это сознательный обмен:
меньше шума в PyDiGraph, богаче исполняемая snapshot-модель.

Данный файл **не отменяет** инвариант reuse: два аспекта с ``user.user_id`` по-прежнему
должны отдавать один и тот же ключ в своих ``context_keys``; мы проверяем
согласованность **на уровне метаданных**, а не подсчётом узлов графа.

═══════════════════════════════════════════════════════════════════════════════
СБРОС КЕША DEPENDENCY FACTORY
═══════════════════════════════════════════════════════════════════════════════

``clear_dependency_factory_cache(coordinator)`` очищает только кеш фабрик
зависимостей на объекте координатора; построенный фасетный граф и снимки
facet’ов не пересобираются — контекстные ключи на аспектах остаются читаемыми.

═══════════════════════════════════════════════════════════════════════════════
ТЕСТОВЫЕ ACTION
═══════════════════════════════════════════════════════════════════════════════

Классы объявляются **внутри модуля теста** (не в tests/domain/), чтобы не
загрязнять доменные фикстуры и держать сценарии узкими:

- один аспект с двумя ключами контекста;
- два аспекта, пересекающиеся по ``user.user_id``;
- ``@on_error`` с собственным набором ключей;
- аспекты без ``@context_requires`` (пустой ``context_keys``).
"""

from pydantic import Field

from action_machine.dependencies.dependency_factory import clear_dependency_factory_cache
from action_machine.graph.gate_coordinator import GateCoordinator
from action_machine.intents.aspects.regular_aspect_decorator import regular_aspect
from action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from action_machine.intents.auth import NoneRole, check_roles
from action_machine.intents.context.context_requires_decorator import context_requires
from action_machine.intents.context.ctx_constants import Ctx
from action_machine.intents.meta.meta_decorator import meta
from action_machine.intents.on_error.on_error_decorator import on_error
from action_machine.model.base_action import BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from action_machine.model.base_state import BaseState
from action_machine.resources.base_resource_manager import BaseResourceManager
from action_machine.runtime.machines.core_action_machine import CoreActionMachine
from action_machine.runtime.tools_box import ToolsBox
from tests.domain_model.domains import SystemDomain


def _regular_aspects(coordinator: GateCoordinator, cls: type):
    snap = coordinator.get_snapshot(cls, "aspect")
    if snap is None or not hasattr(snap, "aspects"):
        return ()
    return tuple(a for a in snap.aspects if a.aspect_type == "regular")


def _error_handlers(coordinator: GateCoordinator, cls: type):
    snap = coordinator.get_snapshot(cls, "error_handler")
    if snap is None or not hasattr(snap, "error_handlers"):
        return ()
    return tuple(snap.error_handlers)


# ═════════════════════════════════════════════════════════════════════════════
# Вспомогательные тестовые компоненты
# ═════════════════════════════════════════════════════════════════════════════


class _CtxTestParams(BaseParams):
    """Параметры для минимальных Action в сценариях context_requires."""

    value: str = Field(description="Тестовое значение")


class _CtxTestResult(BaseResult):
    """Результат для минимальных Action в сценариях context_requires."""

    status: str = Field(description="Статус")


# ═════════════════════════════════════════════════════════════════════════════
# Тестовые Action (узкие edge-case, не выносятся в domain_model)
# ═════════════════════════════════════════════════════════════════════════════


@meta(description="Action с одним аспектом и context_requires", domain=SystemDomain)
@check_roles(NoneRole)
class _SingleContextAction(BaseAction[_CtxTestParams, _CtxTestResult]):
    """Один regular-аспект запрашивает ``user.user_id`` и ``request.trace_id``."""

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
@check_roles(NoneRole)
class _SharedContextFieldAction(BaseAction[_CtxTestParams, _CtxTestResult]):
    """Два аспекта делят ``user.user_id``; второй добавляет ``user.roles``."""

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
@check_roles(NoneRole)
class _ErrorHandlerContextAction(BaseAction[_CtxTestParams, _CtxTestResult]):
    """Обработчик ``ValueError`` требует ``user.user_id`` и ``request.client_ip``."""

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
@check_roles(NoneRole)
class _NoContextAction(BaseAction[_CtxTestParams, _CtxTestResult]):
    """Ни один метод не помечен ``@context_requires`` — ожидаем пустые ``context_keys``."""

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
# Сборка runtime metadata и ключи контекста
# ═════════════════════════════════════════════════════════════════════════════


class TestContextKeysViaMetadata:
    """Проверки ``context_keys`` на аспектах и обработчиках через facet-снимки."""

    def test_aspect_context_keys(self) -> None:
        coordinator = CoreActionMachine.create_coordinator()
        audit = next(
            a for a in _regular_aspects(coordinator,_SingleContextAction)
            if a.method_name == "audit_aspect"
        )
        assert "user.user_id" in audit.context_keys
        assert "request.trace_id" in audit.context_keys

    def test_shared_user_id_across_aspects(self) -> None:
        """Оба аспекта видят ``user.user_id``; расширение ключей только у второго."""

        coordinator = CoreActionMachine.create_coordinator()
        first = next(
            a for a in _regular_aspects(coordinator,_SharedContextFieldAction)
            if a.method_name == "first_aspect"
        )
        second = next(
            a for a in _regular_aspects(coordinator,_SharedContextFieldAction)
            if a.method_name == "second_aspect"
        )
        assert "user.user_id" in first.context_keys
        assert "user.user_id" in second.context_keys
        assert "user.roles" in second.context_keys
        assert "user.roles" not in first.context_keys

    def test_no_context_keys_when_undeclrared(self) -> None:
        """Без декоратора — пустой набор ключей на regular-аспекте."""

        coordinator = CoreActionMachine.create_coordinator()
        simple = next(
            a for a in _regular_aspects(coordinator,_NoContextAction)
            if a.method_name == "simple_aspect"
        )
        assert len(simple.context_keys) == 0

    def test_error_handler_context_keys(self) -> None:
        """``OnErrorMeta`` получает те же строковые пути, что декларировал обработчик."""

        coordinator = CoreActionMachine.create_coordinator()
        handler = next(
            h for h in _error_handlers(coordinator,_ErrorHandlerContextAction)
            if h.method_name == "handle_value_on_error"
        )
        assert "user.user_id" in handler.context_keys
        assert "request.client_ip" in handler.context_keys


class TestContextMetadataAfterFactoryCacheClear:
    """Стабильность ``context_keys`` после сброса кеша dependency factory."""

    def test_reread_context_keys_stable(self) -> None:
        """Повторное чтение из built coordinator стабильно возвращает те же ``context_keys``."""
        coordinator = CoreActionMachine.create_coordinator()
        audit = next(
            a for a in _regular_aspects(coordinator,_SingleContextAction)
            if a.method_name == "audit_aspect"
        )
        assert "user.user_id" in audit.context_keys

    def test_factory_cache_clear_preserves_context_keys(self) -> None:
        """
        Сброс кеша фабрик не ломает чтение контекстных ключей из facet-снимков.
        """
        coordinator = CoreActionMachine.create_coordinator()
        clear_dependency_factory_cache(coordinator)
        audit = next(
            a for a in _regular_aspects(coordinator,_SingleContextAction)
            if a.method_name == "audit_aspect"
        )
        assert "user.user_id" in audit.context_keys
