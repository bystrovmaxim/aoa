# tests/core/test_dependency_factory.py
"""
Тесты DependencyFactory — stateless-фабрика зависимостей.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

DependencyFactory — stateless-фабрика, которая создаёт экземпляры
зависимостей, объявленных через декоратор @depends. Каждый вызов resolve()
создаёт новый экземпляр через factory-функцию или конструктор по умолчанию.
Кеш экземпляров отсутствует — фабрика является чистой функцией.

Фабрика создаётся ``cached_dependency_factory(coordinator, cls)`` из
снимка ``depends`` координатора и передаётся в ToolsBox, откуда аспекты
получают зависимости через box.resolve(PaymentService).

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

Создание из DependencyInfo:
    - Фабрика создаётся из tuple[DependencyInfo, ...].
    - Пустой кортеж — фабрика без зависимостей.

resolve() без factory:
    - Зависимость без factory → конструктор по умолчанию klass().
    - Каждый вызов создаёт новый экземпляр (не синглтон).
    - Передача *args и **kwargs в конструктор.

resolve() с factory:
    - Зависимость с factory → вызывается factory(*args, **kwargs).
    - Lambda-синглтон: factory=lambda: shared_instance.
    - Параметризованная factory: factory=lambda env: Client(env).

resolve() несуществующей зависимости:
    - ValueError с информативным сообщением.

resolve() с rollup:
    - rollup=True для BaseResourceManager → check_rollup_support().
    - rollup=True для не-BaseResourceManager → без проверки.
    - rollup=False → без проверки для любого класса.
    - RollupNotSupportedError для менеджера без поддержки rollup.

Инспекция:
    - has(cls) — проверка наличия зависимости.
    - get_all_classes() — список всех зарегистрированных классов.

Интеграция с доменной моделью:
    - Фабрика из координатора для FullAction содержит PaymentService
      и NotificationService.
"""

import pytest

from action_machine.core.core_action_machine import CoreActionMachine
from action_machine.core.exceptions import RollupNotSupportedError
from action_machine.core.meta_decorator import meta
from action_machine.dependencies.dependency_factory import (
    DependencyFactory,
    DependencyInfo,
    cached_dependency_factory,
)
from action_machine.resource_managers.base_resource_manager import BaseResourceManager
from tests.domain_model import FullAction, NotificationService, PaymentService, PingAction

# ═════════════════════════════════════════════════════════════════════════════
# Вспомогательные классы для тестов
# ═════════════════════════════════════════════════════════════════════════════


class _SimpleService:
    """Простой сервис без конструкторных параметров."""

    pass


class _ConfigurableService:
    """Сервис с параметрами конструктора."""

    def __init__(self, host: str = "localhost", port: int = 8080):
        self.host = host
        self.port = port


@meta(description="Мок-менеджер для тестов rollup")
class _MockResourceManager(BaseResourceManager):
    """Менеджер ресурсов БЕЗ поддержки rollup (по умолчанию)."""

    def get_wrapper_class(self):
        return None


@meta(description="Мок-менеджер с поддержкой rollup")
class _RollupSupportedManager(BaseResourceManager):
    """Менеджер ресурсов С поддержкой rollup."""

    def check_rollup_support(self) -> bool:
        return True

    def get_wrapper_class(self):
        return None


# ═════════════════════════════════════════════════════════════════════════════
# Создание фабрики
# ═════════════════════════════════════════════════════════════════════════════


class TestFactoryCreation:
    """Создание DependencyFactory из DependencyInfo."""

    def test_create_from_dependency_info_tuple(self) -> None:
        """
        Фабрика создаётся из кортежа DependencyInfo.

        Основной формат — tuple[DependencyInfo, ...] из снимка ``depends``
        (или напрямую из ``@depends`` в тестах).
        """
        # Arrange — два DependencyInfo
        deps = (
            DependencyInfo(cls=_SimpleService, description="Простой сервис"),
            DependencyInfo(cls=_ConfigurableService, description="Настраиваемый"),
        )

        # Act — создание фабрики из кортежа
        factory = DependencyFactory(deps)

        # Assert — оба класса зарегистрированы
        assert factory.has(_SimpleService)
        assert factory.has(_ConfigurableService)

    def test_create_from_empty_tuple(self) -> None:
        """
        Пустой кортеж — фабрика без зависимостей.

        Это штатная ситуация: действие без @depends (PingAction)
        получает пустую фабрику.
        """
        # Arrange & Act — пустой кортеж
        factory = DependencyFactory(())

        # Assert — ни одной зависимости
        assert factory.get_all_classes() == []
        assert not factory.has(_SimpleService)


# ═════════════════════════════════════════════════════════════════════════════
# resolve() без factory — конструктор по умолчанию
# ═════════════════════════════════════════════════════════════════════════════


class TestResolveDefault:
    """resolve() без factory — используется конструктор по умолчанию."""

    def test_resolve_creates_new_instance(self) -> None:
        """
        resolve(cls) без factory вызывает cls() — конструктор по умолчанию.

        Каждый вызов создаёт НОВЫЙ экземпляр. Фабрика stateless,
        кеш экземпляров отсутствует.
        """
        # Arrange — фабрика с одной зависимостью без factory
        factory = DependencyFactory((
            DependencyInfo(cls=_SimpleService, description="Сервис"),
        ))

        # Act — два вызова resolve
        first = factory.resolve(_SimpleService)
        second = factory.resolve(_SimpleService)

        # Assert — два разных экземпляра (is-проверка)
        assert isinstance(first, _SimpleService)
        assert isinstance(second, _SimpleService)
        assert first is not second

    def test_resolve_passes_args_to_constructor(self) -> None:
        """
        resolve(cls, *args, **kwargs) передаёт аргументы в конструктор.

        _ConfigurableService(host, port) → экземпляр с заданными параметрами.
        """
        # Arrange — фабрика с ConfigurableService
        factory = DependencyFactory((
            DependencyInfo(cls=_ConfigurableService, description="Настраиваемый"),
        ))

        # Act — resolve с аргументами конструктора
        service = factory.resolve(_ConfigurableService, host="prod.db", port=5432)

        # Assert — аргументы переданы в конструктор
        assert service.host == "prod.db"
        assert service.port == 5432


# ═════════════════════════════════════════════════════════════════════════════
# resolve() с factory
# ═════════════════════════════════════════════════════════════════════════════


class TestResolveWithFactory:
    """resolve() с factory — вызывается пользовательская фабрика."""

    def test_factory_function_called(self) -> None:
        """
        Зависимость с factory → resolve() вызывает factory(), не cls().

        Factory-функция позволяет задать любую логику создания:
        конструктор с параметрами, синглтон, пул, DI-контейнер.
        """
        # Arrange — factory создаёт ConfigurableService с фиксированными параметрами
        factory = DependencyFactory((
            DependencyInfo(
                cls=_ConfigurableService,
                factory=lambda: _ConfigurableService(host="factory-host", port=9999),
                description="Через фабрику",
            ),
        ))

        # Act — resolve вызывает factory, не конструктор напрямую
        service = factory.resolve(_ConfigurableService)

        # Assert — параметры из factory-функции
        assert service.host == "factory-host"
        assert service.port == 9999

    def test_lambda_singleton(self) -> None:
        """
        Lambda-замыкание реализует синглтон: factory=lambda: shared.

        Фреймворк не кеширует — но lambda захватывает один объект,
        и каждый resolve() возвращает один и тот же экземпляр.
        """
        # Arrange — один shared-экземпляр, захваченный lambda
        shared = _SimpleService()
        factory = DependencyFactory((
            DependencyInfo(
                cls=_SimpleService,
                factory=lambda: shared,
                description="Синглтон",
            ),
        ))

        # Act — два вызова resolve
        first = factory.resolve(_SimpleService)
        second = factory.resolve(_SimpleService)

        # Assert — один и тот же объект (синглтон через lambda)
        assert first is shared
        assert second is shared
        assert first is second

    def test_factory_receives_args(self) -> None:
        """
        *args и **kwargs из resolve() передаются в factory().

        Позволяет параметризовать создание зависимости из аспекта:
        box.resolve(Client, "production") → factory("production").
        """
        # Arrange — factory принимает параметр env
        factory = DependencyFactory((
            DependencyInfo(
                cls=_ConfigurableService,
                factory=lambda env: _ConfigurableService(host=f"{env}.db.local"),
                description="Параметризованная фабрика",
            ),
        ))

        # Act — resolve с рантайм-параметром
        service = factory.resolve(_ConfigurableService, "staging")

        # Assert — параметр передан через factory
        assert service.host == "staging.db.local"


# ═════════════════════════════════════════════════════════════════════════════
# resolve() несуществующей зависимости
# ═════════════════════════════════════════════════════════════════════════════


class TestResolveMissing:
    """resolve() для незарегистрированной зависимости."""

    def test_missing_dependency_raises_value_error(self) -> None:
        """
        resolve(cls) для незарегистрированной зависимости → ValueError.

        Сообщение содержит имя запрошенного класса и список доступных
        зависимостей для быстрой диагностики.
        """
        # Arrange — фабрика без _SimpleService
        factory = DependencyFactory((
            DependencyInfo(cls=_ConfigurableService, description="Только это"),
        ))

        # Act & Assert — запрос отсутствующей зависимости
        with pytest.raises(ValueError, match="not declared"):
            factory.resolve(_SimpleService)

    def test_empty_factory_raises_value_error(self) -> None:
        """
        resolve() на пустой фабрике → ValueError.
        """
        # Arrange — пустая фабрика
        factory = DependencyFactory(())

        # Act & Assert
        with pytest.raises(ValueError, match="not declared"):
            factory.resolve(_SimpleService)


# ═════════════════════════════════════════════════════════════════════════════
# resolve() с rollup
# ═════════════════════════════════════════════════════════════════════════════


class TestResolveRollup:
    """resolve() с параметром rollup — проверка поддержки для ресурсных менеджеров."""

    def test_rollup_true_for_supported_manager(self) -> None:
        """
        rollup=True для менеджера с поддержкой rollup → resolve() проходит.

        _RollupSupportedManager переопределяет check_rollup_support()
        и возвращает True. DependencyFactory вызывает check_rollup_support()
        и не бросает исключение.
        """
        # Arrange — фабрика с менеджером, поддерживающим rollup
        factory = DependencyFactory((
            DependencyInfo(cls=_RollupSupportedManager, description="С поддержкой rollup"),
        ))

        # Act — resolve с rollup=True
        manager = factory.resolve(_RollupSupportedManager, rollup=True)

        # Assert — экземпляр создан успешно
        assert isinstance(manager, _RollupSupportedManager)

    def test_rollup_true_for_unsupported_manager_raises(self) -> None:
        """
        rollup=True для менеджера БЕЗ поддержки rollup → RollupNotSupportedError.

        _MockResourceManager не переопределяет check_rollup_support(),
        поэтому используется реализация по умолчанию из BaseResourceManager,
        которая бросает RollupNotSupportedError.
        """
        # Arrange — фабрика с менеджером без поддержки rollup
        factory = DependencyFactory((
            DependencyInfo(cls=_MockResourceManager, description="Без rollup"),
        ))

        # Act & Assert — RollupNotSupportedError
        with pytest.raises(RollupNotSupportedError):
            factory.resolve(_MockResourceManager, rollup=True)

    def test_rollup_true_for_non_resource_manager(self) -> None:
        """
        rollup=True для класса, не наследующего BaseResourceManager →
        проверка rollup НЕ выполняется.

        Проверка check_rollup_support() применяется только к экземплярам
        BaseResourceManager. Обычные сервисы проходят без проверки.
        """
        # Arrange — фабрика с обычным сервисом (не BaseResourceManager)
        factory = DependencyFactory((
            DependencyInfo(cls=_SimpleService, description="Обычный сервис"),
        ))

        # Act — resolve с rollup=True для обычного сервиса
        service = factory.resolve(_SimpleService, rollup=True)

        # Assert — экземпляр создан без ошибок
        assert isinstance(service, _SimpleService)

    def test_rollup_false_skips_check(self) -> None:
        """
        rollup=False → check_rollup_support() НЕ вызывается.

        Даже для менеджера без поддержки rollup: если rollup=False,
        проверка пропускается и экземпляр создаётся штатно.
        """
        # Arrange — фабрика с менеджером без поддержки rollup
        factory = DependencyFactory((
            DependencyInfo(cls=_MockResourceManager, description="Без rollup"),
        ))

        # Act — resolve с rollup=False (по умолчанию)
        manager = factory.resolve(_MockResourceManager, rollup=False)

        # Assert — экземпляр создан без ошибок
        assert isinstance(manager, _MockResourceManager)


# ═════════════════════════════════════════════════════════════════════════════
# Инспекция
# ═════════════════════════════════════════════════════════════════════════════


class TestInspection:
    """Методы инспекции: has(), get_all_classes()."""

    def test_has_returns_true_for_registered(self) -> None:
        """has(cls) → True для зарегистрированной зависимости."""
        # Arrange
        factory = DependencyFactory((
            DependencyInfo(cls=_SimpleService, description="Сервис"),
        ))

        # Act & Assert
        assert factory.has(_SimpleService) is True

    def test_has_returns_false_for_unregistered(self) -> None:
        """has(cls) → False для незарегистрированной зависимости."""
        # Arrange
        factory = DependencyFactory(())

        # Act & Assert
        assert factory.has(_SimpleService) is False

    def test_get_all_classes(self) -> None:
        """get_all_classes() возвращает список всех зарегистрированных классов."""
        # Arrange — фабрика с двумя зависимостями
        factory = DependencyFactory((
            DependencyInfo(cls=_SimpleService, description="A"),
            DependencyInfo(cls=_ConfigurableService, description="B"),
        ))

        # Act
        classes = factory.get_all_classes()

        # Assert — оба класса присутствуют
        assert _SimpleService in classes
        assert _ConfigurableService in classes
        assert len(classes) == 2


# ═════════════════════════════════════════════════════════════════════════════
# Интеграция с доменной моделью через GateCoordinator
# ═════════════════════════════════════════════════════════════════════════════


class TestDomainIntegration:
    """Фабрика из координатора для доменных действий."""

    def test_full_action_factory_has_dependencies(self) -> None:
        """
        ``cached_dependency_factory(coordinator, FullAction)`` содержит PaymentService
        и NotificationService.

        FullAction объявляет @depends(PaymentService) и
        @depends(NotificationService). Координатор собирает метаданные
        и создаёт DependencyFactory с обоими классами.
        """
        # Arrange — координатор, регистрирующий FullAction
        coordinator = CoreActionMachine.create_coordinator()
        factory = cached_dependency_factory(coordinator, FullAction)

        # Act & Assert — оба сервиса зарегистрированы
        assert factory.has(PaymentService)
        assert factory.has(NotificationService)

    def test_ping_action_factory_is_empty(self) -> None:
        """
        ``cached_dependency_factory(coordinator, PingAction)`` — пустая фабрика.

        PingAction не объявляет @depends, поэтому фабрика
        не содержит зависимостей.
        """
        # Arrange — координатор для PingAction без зависимостей
        coordinator = CoreActionMachine.create_coordinator()
        factory = cached_dependency_factory(coordinator, PingAction)

        # Act & Assert — фабрика пуста
        assert factory.get_all_classes() == []

    def test_factory_creates_payment_service(self) -> None:
        """
        factory.resolve(PaymentService) создаёт экземпляр PaymentService.

        Это реальный resolve через конструктор по умолчанию, без моков.
        """
        # Arrange — фабрика из координатора
        coordinator = CoreActionMachine.create_coordinator()
        factory = cached_dependency_factory(coordinator, FullAction)

        # Act — resolve реального сервиса
        service = factory.resolve(PaymentService)

        # Assert — экземпляр создан
        assert isinstance(service, PaymentService)
