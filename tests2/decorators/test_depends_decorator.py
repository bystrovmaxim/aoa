# tests2/decorators/test_depends_decorator.py
"""
Тесты декоратора @depends — объявление зависимости действия от внешнего сервиса.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Декоратор @depends прикрепляет к классу действия информацию о требуемой
зависимости. При выполнении машина читает список зависимостей через
ClassMetadata, создаёт DependencyFactory и передаёт в ToolsBox.

Декоратор при применении:
1. Проверяет, что klass — класс (type).
2. Проверяет, что целевой класс наследует DependencyGateHost.
3. Проверяет, что klass — подкласс верхней границы (bound) из generic.
4. Проверяет отсутствие дубликатов.
5. Записывает DependencyInfo в cls._depends_info.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

Валидные аргументы:
    - Зависимость без factory — конструктор по умолчанию.
    - Зависимость с factory — lambda или callable.
    - Зависимость с description.
    - Несколько @depends на одном классе.

Наследование зависимостей:
    - Дочерний класс наследует зависимости родителя.
    - Дочерний класс добавляет свои зависимости без мутации родителя.

Невалидные аргументы:
    - klass не type → TypeError.
    - klass не подкласс bound → TypeError.
    - description не строка → TypeError.
    - Дублирование зависимости → ValueError.

Невалидные цели:
    - Применён к функции → TypeError.
    - Класс не наследует DependencyGateHost → TypeError.

Интеграция:
    - MetadataBuilder собирает dependencies из _depends_info.
    - GateCoordinator.get_factory() создаёт DependencyFactory.
"""

import pytest

from action_machine.aspects.summary_aspect import summary_aspect
from action_machine.auth import ROLE_NONE, check_roles
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.core.gate_coordinator import GateCoordinator
from action_machine.core.meta_decorator import meta
from action_machine.dependencies.dependency_gate_host import DependencyGateHost
from action_machine.dependencies.depends import depends
from tests2.domain import FullAction, NotificationService, PaymentService

# ═════════════════════════════════════════════════════════════════════════════
# Вспомогательные классы
# ═════════════════════════════════════════════════════════════════════════════


class _ServiceA:
    """Простой сервис для тестов."""
    pass


class _ServiceB:
    """Второй сервис для тестов множественных зависимостей."""
    pass


# ═════════════════════════════════════════════════════════════════════════════
# Валидные аргументы
# ═════════════════════════════════════════════════════════════════════════════


class TestValidArgs:
    """Декоратор принимает валидные аргументы и записывает _depends_info."""

    def test_basic_dependency(self) -> None:
        """
        @depends(ServiceA) — минимальный вызов, без factory и description.

        DependencyInfo(cls=ServiceA, factory=None, description="")
        записывается в cls._depends_info.
        """
        # Arrange & Act
        @meta(description="Тест")
        @check_roles(ROLE_NONE)
        @depends(_ServiceA)
        class _Action(BaseAction[BaseParams, BaseResult]):
            @summary_aspect("test")
            async def summary(self, params, state, box, connections):
                return BaseResult()

        # Assert — _depends_info содержит одну зависимость
        assert hasattr(_Action, "_depends_info")
        assert len(_Action._depends_info) == 1
        assert _Action._depends_info[0].cls is _ServiceA
        assert _Action._depends_info[0].factory is None
        assert _Action._depends_info[0].description == ""

    def test_dependency_with_factory(self) -> None:
        """
        @depends(ServiceA, factory=lambda: ServiceA()) — с factory.

        Factory вызывается вместо конструктора при resolve().
        """
        # Arrange
        def factory_fn():
            return _ServiceA()

        # Act
        @meta(description="Тест")
        @check_roles(ROLE_NONE)
        @depends(_ServiceA, factory=factory_fn)
        class _Action(BaseAction[BaseParams, BaseResult]):
            @summary_aspect("test")
            async def summary(self, params, state, box, connections):
                return BaseResult()

        # Assert — factory записана
        assert _Action._depends_info[0].factory is factory_fn

    def test_dependency_with_description(self) -> None:
        """
        @depends(ServiceA, description="Описание") — с описанием.

        Description используется в графе координатора и интроспекции.
        """
        # Arrange & Act
        @meta(description="Тест")
        @check_roles(ROLE_NONE)
        @depends(_ServiceA, description="Сервис обработки платежей")
        class _Action(BaseAction[BaseParams, BaseResult]):
            @summary_aspect("test")
            async def summary(self, params, state, box, connections):
                return BaseResult()

        # Assert — description записан
        assert _Action._depends_info[0].description == "Сервис обработки платежей"

    def test_multiple_dependencies(self) -> None:
        """
        Несколько @depends на одном классе — все записываются в _depends_info.

        Порядок зависимостей соответствует порядку применения декораторов
        (снизу вверх, т.к. декораторы применяются от ближнего к дальнему).
        """
        # Arrange & Act
        @meta(description="Тест")
        @check_roles(ROLE_NONE)
        @depends(_ServiceA, description="A")
        @depends(_ServiceB, description="B")
        class _Action(BaseAction[BaseParams, BaseResult]):
            @summary_aspect("test")
            async def summary(self, params, state, box, connections):
                return BaseResult()

        # Assert — обе зависимости записаны
        assert len(_Action._depends_info) == 2
        classes = [d.cls for d in _Action._depends_info]
        assert _ServiceA in classes
        assert _ServiceB in classes

    def test_returns_class_unchanged(self) -> None:
        """
        Декоратор возвращает класс без изменений — только добавляет _depends_info.
        """
        # Arrange
        @meta(description="Тест")
        @check_roles(ROLE_NONE)
        class _Original(BaseAction[BaseParams, BaseResult]):
            custom = 99

            @summary_aspect("test")
            async def summary(self, params, state, box, connections):
                return BaseResult()

        # Act
        _Decorated = depends(_ServiceA)(_Original)

        # Assert — тот же класс
        assert _Decorated is _Original
        assert _Decorated.custom == 99


# ═════════════════════════════════════════════════════════════════════════════
# Наследование зависимостей
# ═════════════════════════════════════════════════════════════════════════════


class TestInheritance:
    """Дочерний класс наследует зависимости родителя."""

    def test_child_inherits_parent_dependencies(self) -> None:
        """
        Дочерний класс без @depends видит зависимости родителя через getattr.

        MetadataBuilder использует getattr(cls, "_depends_info", []),
        который обходит MRO и находит _depends_info на родителе.
        """
        # Arrange
        @meta(description="Родитель")
        @check_roles(ROLE_NONE)
        @depends(_ServiceA)
        class _Parent(BaseAction[BaseParams, BaseResult]):
            @summary_aspect("test")
            async def summary(self, params, state, box, connections):
                return BaseResult()

        @meta(description="Дочерний")
        @check_roles(ROLE_NONE)
        class _Child(_Parent):
            pass

        # Act — getattr обходит MRO
        child_deps = getattr(_Child, "_depends_info", [])

        # Assert — дочерний класс видит зависимости родителя
        assert len(child_deps) == 1
        assert child_deps[0].cls is _ServiceA

    def test_child_adds_without_mutating_parent(self) -> None:
        """
        @depends на дочернем классе не мутирует _depends_info родителя.

        При первом применении @depends к подклассу декоратор копирует
        родительский список в собственный __dict__, затем добавляет
        новую зависимость в копию.
        """
        # Arrange
        @meta(description="Родитель")
        @check_roles(ROLE_NONE)
        @depends(_ServiceA)
        class _Parent(BaseAction[BaseParams, BaseResult]):
            @summary_aspect("test")
            async def summary(self, params, state, box, connections):
                return BaseResult()

        # Act — дочерний добавляет ServiceB
        @meta(description="Дочерний")
        @check_roles(ROLE_NONE)
        @depends(_ServiceB)
        class _Child(_Parent):
            pass

        # Assert — родитель не изменился (только ServiceA)
        parent_deps = _Parent.__dict__.get("_depends_info", [])
        assert len(parent_deps) == 1
        assert parent_deps[0].cls is _ServiceA

        # Assert — дочерний имеет обе зависимости (ServiceA + ServiceB)
        child_deps = _Child._depends_info
        assert len(child_deps) == 2


# ═════════════════════════════════════════════════════════════════════════════
# Невалидные аргументы
# ═════════════════════════════════════════════════════════════════════════════


class TestInvalidArgs:
    """Невалидные аргументы → TypeError или ValueError."""

    def test_klass_not_type_raises_type_error(self) -> None:
        """
        @depends("строка") → TypeError.

        klass должен быть классом (type), не экземпляром или строкой.
        """
        # Arrange & Act & Assert
        with pytest.raises(TypeError, match="ожидает класс"):
            depends("not_a_class")

    def test_klass_instance_raises_type_error(self) -> None:
        """
        @depends(ServiceA()) → TypeError.

        Передан экземпляр, а не класс.
        """
        # Arrange & Act & Assert
        with pytest.raises(TypeError, match="ожидает класс"):
            depends(_ServiceA())

    def test_description_not_string_raises_type_error(self) -> None:
        """
        @depends(ServiceA, description=42) → TypeError.
        """
        # Arrange & Act & Assert
        with pytest.raises(TypeError, match="description должен быть строкой"):
            depends(_ServiceA, description=42)

    def test_duplicate_dependency_raises_value_error(self) -> None:
        """
        Два @depends(ServiceA) на одном классе → ValueError.

        Дублирование зависимостей — вероятная ошибка разработчика.
        """
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match="уже объявлен"):
            @depends(_ServiceA)
            @depends(_ServiceA)
            class _Action(DependencyGateHost[object]):
                pass


# ═════════════════════════════════════════════════════════════════════════════
# Невалидные цели
# ═════════════════════════════════════════════════════════════════════════════


class TestInvalidTarget:
    """Декоратор применён к невалидной цели → TypeError."""

    def test_applied_to_function_raises_type_error(self) -> None:
        """
        @depends(ServiceA) на функции → TypeError.
        """
        # Arrange & Act & Assert
        with pytest.raises(TypeError, match="только к классу"):
            @depends(_ServiceA)
            def _func():
                pass

    def test_applied_to_class_without_gate_host_raises(self) -> None:
        """
        @depends(ServiceA) на классе без DependencyGateHost → TypeError.
        """
        # Arrange & Act & Assert
        with pytest.raises(TypeError, match="не наследует DependencyGateHost"):
            @depends(_ServiceA)
            class _Plain:
                pass


# ═════════════════════════════════════════════════════════════════════════════
# Bound — ограничитель типа зависимостей
# ═════════════════════════════════════════════════════════════════════════════


class TestDependsBound:
    """Проверка bound — верхней границы типа зависимостей из DependencyGateHost[T]."""

    def test_base_action_bound_is_object(self) -> None:
        """
        BaseAction наследует DependencyGateHost[object] — любой класс допустим.
        """
        # Arrange & Act & Assert
        assert BaseAction.get_depends_bound() is object

    def test_custom_bound_rejects_wrong_type(self) -> None:
        """
        DependencyGateHost[BaseResourceManager] — только подклассы
        BaseResourceManager допустимы как зависимости.

        Попытка добавить обычный класс → TypeError.
        """
        # Arrange
        from action_machine.resource_managers.base_resource_manager import BaseResourceManager

        class _RestrictedHost(DependencyGateHost[BaseResourceManager]):
            pass

        # Act & Assert — _ServiceA не наследует BaseResourceManager
        with pytest.raises(TypeError, match="не является подклассом"):
            @depends(_ServiceA)
            class _Action(_RestrictedHost):
                pass


# ═════════════════════════════════════════════════════════════════════════════
# Интеграция с MetadataBuilder и GateCoordinator
# ═════════════════════════════════════════════════════════════════════════════


class TestMetadataIntegration:
    """_depends_info корректно собирается в ClassMetadata.dependencies."""

    def test_domain_action_dependencies(self) -> None:
        """
        FullAction из доменной модели имеет PaymentService и NotificationService.
        """
        # Arrange
        coordinator = GateCoordinator()

        # Act
        metadata = coordinator.get(FullAction)

        # Assert — две зависимости
        assert metadata.has_dependencies()
        dep_classes = metadata.get_dependency_classes()
        assert PaymentService in dep_classes
        assert NotificationService in dep_classes

    def test_factory_created_from_dependencies(self) -> None:
        """
        GateCoordinator.get_factory() создаёт DependencyFactory
        из metadata.dependencies.
        """
        # Arrange
        coordinator = GateCoordinator()

        # Act
        factory = coordinator.get_factory(FullAction)

        # Assert — фабрика содержит оба сервиса
        assert factory.has(PaymentService)
        assert factory.has(NotificationService)
