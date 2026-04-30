# tests/scenarios/dependencies/test_dependency_factory_core_machine.py
"""
Tests for DependencyFactory — a stateless dependency factory.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

DependencyFactory is a stateless factory that creates instances of dependencies
declared via the @depends decorator. Each resolve() call creates a new instance
via a factory function or the default constructor.
There is no instance cache — the factory behaves as a pure function.

The factory is built with ``cached_dependency_factory(coordinator, cls)`` from
the coordinator's ``depends`` snapshot and passed into ToolsBox; aspects then
obtain dependencies via ``box.resolve(PaymentServiceResource)`` (the
``@depends`` resource class; use ``.service`` for the client when applicable).

═══════════════════════════════════════════════════════════════════════════════
SCENARIOS COVERED
═══════════════════════════════════════════════════════════════════════════════

Creation from DependencyInfo:
    - Factory is built from tuple[DependencyInfo, ...].
    - Empty tuple — factory with no dependencies.

resolve() without factory:
    - Dependency without factory → default constructor klass().
    - Each call creates a new instance (not a singleton).
    - *args and **kwargs are passed to the constructor.

resolve() with factory:
    - Dependency with factory → factory(*args, **kwargs) is called.
    - Lambda singleton: factory=lambda: shared_instance.
    - Parameterized factory: factory=lambda env: Client(env).

resolve() for a missing dependency:
    - ValueError with an informative message.

resolve() with rollup:
    - rollup=True for BaseResource → check_rollup_support().
    - rollup=True for non-BaseResource → no check.
    - rollup=False → no check for any class.
    - RollupNotSupportedError for a manager without rollup support.

Inspection:
    - has(cls) — whether the dependency is registered.
    - get_all_classes() — list of all registered classes.

Integration with the domain model:
    - Factory from the coordinator for FullAction includes PaymentService
      and NotificationService.
"""

import pytest

from action_machine.exceptions import RollupNotSupportedError
from action_machine.intents.meta.meta_decorator import meta
from action_machine.legacy.core import Core
from action_machine.resources.base_resource import BaseResource
from action_machine.runtime.dependency_factory import (
    DependencyFactory,
    cached_dependency_factory,
)
from action_machine.runtime.dependency_info import DependencyInfo
from graph.graph_coordinator import GraphCoordinator
from tests.scenarios.domain_model import (
    FullAction,
    NotificationServiceResource,
    OrdersDbManager,
    PaymentServiceResource,
    PingAction,
)
from tests.scenarios.domain_model.domains import TestDomain

# ═════════════════════════════════════════════════════════════════════════════
# Test helper classes
# ═════════════════════════════════════════════════════════════════════════════


class _SimpleService:
    """Simple service with no constructor parameters."""

    pass


class _ConfigurableService:
    """Service with constructor parameters."""

    def __init__(self, host: str = "localhost", port: int = 8080):
        self.host = host
        self.port = port


@meta(description="Mock manager for rollup tests", domain=TestDomain)
class _MockResourceManager(BaseResource):
    """Resource manager WITHOUT rollup support (default)."""

    def get_wrapper_class(self):
        return None


@meta(description="Mock manager with rollup support", domain=TestDomain)
class _RollupSupportedManager(BaseResource):
    """Resource manager WITH rollup support."""

    def check_rollup_support(self) -> bool:
        return True

    def get_wrapper_class(self):
        return None


# ═════════════════════════════════════════════════════════════════════════════
# Factory creation
# ═════════════════════════════════════════════════════════════════════════════


class TestFactoryCreation:
    """Creating DependencyFactory from DependencyInfo."""

    def test_create_from_dependency_info_tuple(self) -> None:
        """
        Factory is built from a tuple of DependencyInfo.

        The primary format is tuple[DependencyInfo, ...] from the ``depends``
        snapshot (or directly from ``@depends`` in tests).
        """
        # Arrange — two DependencyInfo entries
        deps = (
            DependencyInfo(cls=_SimpleService, description="Simple service"),
            DependencyInfo(cls=_ConfigurableService, description="Configurable"),
        )

        # Act — create factory from tuple
        factory = DependencyFactory(deps)

        # Assert — both classes registered
        assert factory.has(_SimpleService)
        assert factory.has(_ConfigurableService)

    def test_create_from_empty_tuple(self) -> None:
        """
        Empty tuple — factory with no dependencies.

        This is normal: an action without @depends (PingAction)
        gets an empty factory.
        """
        # Arrange & Act — empty tuple
        factory = DependencyFactory(())

        # Assert — no dependencies
        assert factory.get_all_classes() == []
        assert not factory.has(_SimpleService)


# ═════════════════════════════════════════════════════════════════════════════
# resolve() without factory — default constructor
# ═════════════════════════════════════════════════════════════════════════════


class TestResolveDefault:
    """resolve() without factory — default constructor is used."""

    def test_resolve_creates_new_instance(self) -> None:
        """
        resolve(cls) without factory calls cls() — the default constructor.

        Each call creates a NEW instance. The factory is stateless;
        there is no instance cache.
        """
        # Arrange — factory with one dependency and no factory
        factory = DependencyFactory((
            DependencyInfo(cls=_SimpleService, description="Service"),
        ))

        # Act — two resolve calls
        first = factory.resolve(_SimpleService)
        second = factory.resolve(_SimpleService)

        # Assert — two distinct instances (identity check)
        assert isinstance(first, _SimpleService)
        assert isinstance(second, _SimpleService)
        assert first is not second

    def test_resolve_passes_args_to_constructor(self) -> None:
        """
        resolve(cls, *args, **kwargs) forwards arguments to the constructor.

        _ConfigurableService(host, port) → instance with the given parameters.
        """
        # Arrange — factory with ConfigurableService
        factory = DependencyFactory((
            DependencyInfo(cls=_ConfigurableService, description="Configurable"),
        ))

        # Act — resolve with constructor arguments
        service = factory.resolve(_ConfigurableService, host="prod.db", port=5432)

        # Assert — arguments passed to constructor
        assert service.host == "prod.db"
        assert service.port == 5432


# ═════════════════════════════════════════════════════════════════════════════
# resolve() with factory
# ═════════════════════════════════════════════════════════════════════════════


class TestResolveWithFactory:
    """resolve() with factory — user-defined factory is invoked."""

    def test_factory_function_called(self) -> None:
        """
        Dependency with factory → resolve() calls factory(), not cls().

        A factory function can implement any creation logic:
        constructor with parameters, singleton, pool, DI container.
        """
        # Arrange — factory builds ConfigurableService with fixed parameters
        factory = DependencyFactory((
            DependencyInfo(
                cls=_ConfigurableService,
                factory=lambda: _ConfigurableService(host="factory-host", port=9999),
                description="Via factory",
            ),
        ))

        # Act — resolve invokes factory, not the constructor directly
        service = factory.resolve(_ConfigurableService)

        # Assert — parameters from factory function
        assert service.host == "factory-host"
        assert service.port == 9999

    def test_lambda_singleton(self) -> None:
        """
        A lambda closure implements singleton semantics: factory=lambda: shared.

        The framework does not cache — but the lambda captures one object,
        and every resolve() returns the same instance.
        """
        # Arrange — one shared instance captured by lambda
        shared = _SimpleService()
        factory = DependencyFactory((
            DependencyInfo(
                cls=_SimpleService,
                factory=lambda: shared,
                description="Singleton",
            ),
        ))

        # Act — two resolve calls
        first = factory.resolve(_SimpleService)
        second = factory.resolve(_SimpleService)

        # Assert — same object (singleton via lambda)
        assert first is shared
        assert second is shared
        assert first is second

    def test_factory_receives_args(self) -> None:
        """
        *args and **kwargs from resolve() are passed to factory().

        Allows parameterizing dependency creation from an aspect:
        box.resolve(Client, "production") → factory("production").
        """
        # Arrange — factory accepts env parameter
        factory = DependencyFactory((
            DependencyInfo(
                cls=_ConfigurableService,
                factory=lambda env: _ConfigurableService(host=f"{env}.db.local"),
                description="Parameterized factory",
            ),
        ))

        # Act — resolve with runtime parameter
        service = factory.resolve(_ConfigurableService, "staging")

        # Assert — parameter forwarded through factory
        assert service.host == "staging.db.local"


# ═════════════════════════════════════════════════════════════════════════════
# resolve() for a missing dependency
# ═════════════════════════════════════════════════════════════════════════════


class TestResolveMissing:
    """resolve() for an unregistered dependency."""

    def test_missing_dependency_raises_value_error(self) -> None:
        """
        resolve(cls) for an unregistered dependency → ValueError.

        The message includes the requested class name and the list of available
        dependencies for quick diagnosis.
        """
        # Arrange — factory without _SimpleService
        factory = DependencyFactory((
            DependencyInfo(cls=_ConfigurableService, description="Only this"),
        ))

        # Act & Assert — request missing dependency
        with pytest.raises(ValueError, match="not declared"):
            factory.resolve(_SimpleService)

    def test_empty_factory_raises_value_error(self) -> None:
        """
        resolve() on an empty factory → ValueError.
        """
        # Arrange — empty factory
        factory = DependencyFactory(())

        # Act & Assert
        with pytest.raises(ValueError, match="not declared"):
            factory.resolve(_SimpleService)


# ═════════════════════════════════════════════════════════════════════════════
# resolve() with rollup
# ═════════════════════════════════════════════════════════════════════════════


class TestResolveRollup:
    """resolve() with rollup — support check for resource managers."""

    def test_rollup_true_for_supported_manager(self) -> None:
        """
        rollup=True for a manager that supports rollup → resolve() succeeds.

        _RollupSupportedManager overrides check_rollup_support()
        and returns True. DependencyFactory calls check_rollup_support()
        and does not raise.
        """
        # Arrange — factory with rollup-capable manager
        factory = DependencyFactory((
            DependencyInfo(cls=_RollupSupportedManager, description="With rollup support"),
        ))

        # Act — resolve with rollup=True
        manager = factory.resolve(_RollupSupportedManager, rollup=True)

        # Assert — instance created successfully
        assert isinstance(manager, _RollupSupportedManager)

    def test_rollup_true_for_unsupported_manager_raises(self) -> None:
        """
        rollup=True for a manager WITHOUT rollup support → RollupNotSupportedError.

        _MockResourceManager does not override check_rollup_support(),
        so the default from BaseResource applies,
        which raises RollupNotSupportedError.
        """
        # Arrange — factory with manager without rollup support
        factory = DependencyFactory((
            DependencyInfo(cls=_MockResourceManager, description="Without rollup"),
        ))

        # Act & Assert — RollupNotSupportedError
        with pytest.raises(RollupNotSupportedError):
            factory.resolve(_MockResourceManager, rollup=True)

    def test_rollup_true_for_non_resource_manager(self) -> None:
        """
        rollup=True for a class that does not inherit BaseResource →
        rollup check is NOT performed.

        check_rollup_support() applies only to BaseResource instances.
        Ordinary services resolve without that check.
        """
        # Arrange — factory with ordinary service (not BaseResource)
        factory = DependencyFactory((
            DependencyInfo(cls=_SimpleService, description="Ordinary service"),
        ))

        # Act — resolve with rollup=True for ordinary service
        service = factory.resolve(_SimpleService, rollup=True)

        # Assert — instance created without error
        assert isinstance(service, _SimpleService)

    def test_rollup_false_skips_check(self) -> None:
        """
        rollup=False → check_rollup_support() is NOT called.

        Even for a manager without rollup support: if rollup=False,
        the check is skipped and the instance is created normally.
        """
        # Arrange — factory with manager without rollup support
        factory = DependencyFactory((
            DependencyInfo(cls=_MockResourceManager, description="Without rollup"),
        ))

        # Act — resolve with rollup=False (default)
        manager = factory.resolve(_MockResourceManager, rollup=False)

        # Assert — instance created without error
        assert isinstance(manager, _MockResourceManager)


# ═════════════════════════════════════════════════════════════════════════════
# Inspection
# ═════════════════════════════════════════════════════════════════════════════


class TestInspection:
    """Inspection methods: has(), get_all_classes()."""

    def test_has_returns_true_for_registered(self) -> None:
        """has(cls) → True for a registered dependency."""
        # Arrange
        factory = DependencyFactory((
            DependencyInfo(cls=_SimpleService, description="Service"),
        ))

        # Act & Assert
        assert factory.has(_SimpleService) is True

    def test_has_returns_false_for_unregistered(self) -> None:
        """has(cls) → False for an unregistered dependency."""
        # Arrange
        factory = DependencyFactory(())

        # Act & Assert
        assert factory.has(_SimpleService) is False

    def test_get_all_classes(self) -> None:
        """get_all_classes() returns all registered classes."""
        # Arrange — factory with two dependencies
        factory = DependencyFactory((
            DependencyInfo(cls=_SimpleService, description="A"),
            DependencyInfo(cls=_ConfigurableService, description="B"),
        ))

        # Act
        classes = factory.get_all_classes()

        # Assert — both classes present
        assert _SimpleService in classes
        assert _ConfigurableService in classes
        assert len(classes) == 2


# ═════════════════════════════════════════════════════════════════════════════
# Integration with domain model via GraphCoordinator
# ═════════════════════════════════════════════════════════════════════════════


class TestDomainIntegration:
    """Factory from coordinator for domain actions."""

    def test_full_action_factory_has_dependencies(self) -> None:
        """
        ``cached_dependency_factory(coordinator, FullAction)`` includes PaymentService
        and NotificationService.

        FullAction declares ``@depends`` on ``PaymentServiceResource``,
        ``NotificationServiceResource``, and ``OrdersDbManager``. The coordinator
        collects metadata and builds a DependencyFactory with those classes.
        """
        # Arrange — coordinator registering FullAction
        coordinator = Core.create_coordinator()
        factory = cached_dependency_factory(coordinator, FullAction)

        # Act & Assert — services and resource manager type registered
        assert factory.has(PaymentServiceResource)
        assert factory.has(NotificationServiceResource)
        assert factory.has(OrdersDbManager)

    def test_ping_action_factory_is_empty(self) -> None:
        """
        ``cached_dependency_factory(coordinator, PingAction)`` is an empty factory.

        PingAction does not declare @depends, so the factory
        has no dependencies.
        """
        # Arrange — coordinator for PingAction without dependencies
        coordinator = Core.create_coordinator()
        factory = cached_dependency_factory(coordinator, PingAction)

        # Act & Assert — factory is empty
        assert factory.get_all_classes() == []

    def test_factory_creates_payment_service(self) -> None:
        """
        factory.resolve(PaymentServiceResource) creates a PaymentServiceResource.

        Real resolve via default factory from ``@depends``, no mocks.
        """
        # Arrange — factory from coordinator
        coordinator = Core.create_coordinator()
        factory = cached_dependency_factory(coordinator, FullAction)

        # Act — resolve real service
        service = factory.resolve(PaymentServiceResource)

        # Assert — instance created
        assert isinstance(service, PaymentServiceResource)


def test_cached_dependency_factory_raises_when_graph_not_built() -> None:
    coordinator = GraphCoordinator()
    assert coordinator.is_built is False

    with pytest.raises(RuntimeError, match="not built"):
        cached_dependency_factory(coordinator, PingAction)


def test_cached_dependency_factory_fallback_when_snapshot_missing_dependencies_mapping(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    coordinator = Core.create_coordinator()

    monkeypatch.setattr(coordinator, "get_snapshot", lambda cls, facet: object())

    factory = cached_dependency_factory(coordinator, PingAction)
    assert factory.get_all_classes() == []

    factory_repeat = cached_dependency_factory(coordinator, PingAction)
    assert factory_repeat is factory
