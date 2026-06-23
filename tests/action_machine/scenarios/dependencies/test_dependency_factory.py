# tests/scenarios/dependencies/test_dependency_factory.py
"""
Tests for DependencyFactory — stateless factory for creating dependency instances.

DependencyFactory accepts a tuple of DependencyInfo (from coordinator snapshots) and
provides resolve() to create instances. Each resolve() call creates a new
instance — no caching. Supports custom factory functions, rollup checking for
BaseResource subclasses, and both DependencyInfo tuples and legacy
dict-based input formats.

Scenarios covered:
    - resolve() with default constructor creates a new instance each call.
    - resolve() with custom factory calls the factory function.
    - resolve() passes *args and **kwargs to factory/constructor.
    - resolve() for unregistered class raises ValueError.
    - rollup=True on a BaseResource subclass calls check_rollup_support.
    - rollup=True on a non-BaseResource is ignored (no error).
    - has() returns True for registered and False for unregistered classes.
    - get_all_classes() returns all registered dependency classes.
    - Legacy dict format is accepted and converted to DependencyInfo.
    - Factory lambda for singleton pattern returns the same instance.
    - DependencyInfo is frozen (immutable).
"""


import pytest

from aoa.action_machine.intents.meta.meta_decorator import meta
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.runtime.dependency_factory import DependencyFactory
from aoa.action_machine.runtime.dependency_info import DependencyInfo
from tests.action_machine.scenarios.domain_model.domains import TestDomain

# ─────────────────────────────────────────────────────────────────────────────
# Helper classes — intentionally simple, defined here for isolation.
# ─────────────────────────────────────────────────────────────────────────────


class _SimpleService:
    """A plain service class with a default constructor."""

    def __init__(self, name: str = "default") -> None:
        self.name = name


class _NoArgService:
    """A service with no constructor arguments."""

    pass


@meta(description="Fake resource manager for dependency factory tests", domain=TestDomain)
class _FakeResourceManager(BaseResource):
    """A fake resource manager that supports rollup."""

    def get_wrapper_class(self):
        return None

    async def check_rollup_support(self) -> bool:
        return True


@meta(description="Unsupported resource manager for dependency factory tests", domain=TestDomain)
class _UnsupportedManager(BaseResource):
    """A resource manager that does NOT support rollup."""

    def get_wrapper_class(self):
        return None

    async def check_rollup_support(self) -> bool:
        from aoa.action_machine.exceptions import HandleError

        raise HandleError("Rollup not supported")


# ═════════════════════════════════════════════════════════════════════════════
# resolve() with default constructor
# ═════════════════════════════════════════════════════════════════════════════


class TestResolveDefault:
    """Verify resolve() creates instances via default constructor."""

    async def test_creates_instance(self) -> None:
        """resolve() returns an instance of the requested class."""
        factory = DependencyFactory((DependencyInfo(cls=_SimpleService),))

        instance = await factory.resolve(_SimpleService)
        assert isinstance(instance, _SimpleService)

    async def test_new_instance_each_call(self) -> None:
        """Each resolve() call returns a new instance (no caching)."""
        factory = DependencyFactory((DependencyInfo(cls=_SimpleService),))

        a = await factory.resolve(_SimpleService)
        b = await factory.resolve(_SimpleService)
        assert a is not b

    async def test_passes_args(self) -> None:
        """Positional arguments are forwarded to the constructor."""
        factory = DependencyFactory((DependencyInfo(cls=_SimpleService),))

        instance = await factory.resolve(_SimpleService, "custom_name")
        assert instance.name == "custom_name"

    async def test_passes_kwargs(self) -> None:
        """Keyword arguments are forwarded to the constructor."""
        factory = DependencyFactory((DependencyInfo(cls=_SimpleService),))

        instance = await factory.resolve(_SimpleService, name="kw_name")
        assert instance.name == "kw_name"

    async def test_no_arg_service(self) -> None:
        """A service with no constructor args is created correctly."""
        factory = DependencyFactory((DependencyInfo(cls=_NoArgService),))

        instance = await factory.resolve(_NoArgService)
        assert isinstance(instance, _NoArgService)


# ═════════════════════════════════════════════════════════════════════════════
# resolve() with custom factory
# ═════════════════════════════════════════════════════════════════════════════


class TestResolveWithFactory:
    """Verify resolve() delegates to custom factory functions."""

    async def test_uses_factory(self) -> None:
        """When factory is provided, it is called instead of the constructor."""
        factory = DependencyFactory(
            (
                DependencyInfo(
                    cls=_SimpleService,
                    factory=lambda: _SimpleService(name="from_factory"),
                ),
            )
        )

        instance = await factory.resolve(_SimpleService)
        assert instance.name == "from_factory"

    async def test_factory_receives_args(self) -> None:
        """Factory receives *args and **kwargs from resolve()."""
        factory = DependencyFactory(
            (
                DependencyInfo(
                    cls=_SimpleService,
                    factory=lambda n: _SimpleService(name=n),
                ),
            )
        )

        instance = await factory.resolve(_SimpleService, "arg_name")
        assert instance.name == "arg_name"

    async def test_singleton_via_lambda(self) -> None:
        """A lambda closure can implement singleton pattern."""
        shared = _SimpleService(name="shared")

        factory = DependencyFactory((DependencyInfo(cls=_SimpleService, factory=lambda: shared),))

        a = await factory.resolve(_SimpleService)
        b = await factory.resolve(_SimpleService)
        assert a is b
        assert a is shared


# ═════════════════════════════════════════════════════════════════════════════
# resolve() for unregistered dependency
# ═════════════════════════════════════════════════════════════════════════════


class TestResolveUnregistered:
    """Verify that resolving an unregistered class raises ValueError."""

    async def test_raises_value_error(self) -> None:
        """Resolving a class not in @depends raises ValueError."""
        factory = DependencyFactory((DependencyInfo(cls=_SimpleService),))

        with pytest.raises(ValueError, match="not declared"):
            await factory.resolve(_NoArgService)

    async def test_empty_factory(self) -> None:
        """An empty factory raises ValueError for any class."""
        factory = DependencyFactory(())

        with pytest.raises(ValueError):
            await factory.resolve(_SimpleService)


# ═════════════════════════════════════════════════════════════════════════════
# Rollup support
# ═════════════════════════════════════════════════════════════════════════════


class TestRollupSupport:
    """Verify rollup checking for BaseResource instances."""

    async def test_rollup_true_calls_check(self) -> None:
        """rollup=True on a resource manager calls check_rollup_support."""
        factory = DependencyFactory((DependencyInfo(cls=_FakeResourceManager),))

        # Should not raise — _FakeResourceManager supports rollup
        instance = await factory.resolve(_FakeResourceManager, rollup=True)
        assert isinstance(instance, _FakeResourceManager)

    async def test_rollup_true_on_non_manager_is_safe(self) -> None:
        """rollup=True on a non-BaseResource is silently ignored."""
        factory = DependencyFactory((DependencyInfo(cls=_SimpleService),))

        # Should not raise — _SimpleService is not a BaseResource
        instance = await factory.resolve(_SimpleService, rollup=True)
        assert isinstance(instance, _SimpleService)

    async def test_rollup_false_skips_check(self) -> None:
        """rollup=False (default) does not call check_rollup_support."""
        factory = DependencyFactory((DependencyInfo(cls=_UnsupportedManager),))

        # Should not raise — rollup check is skipped
        instance = await factory.resolve(_UnsupportedManager, rollup=False)
        assert isinstance(instance, _UnsupportedManager)


# ═════════════════════════════════════════════════════════════════════════════
# has() and get_all_classes()
# ═════════════════════════════════════════════════════════════════════════════


class TestIntrospection:
    """Verify has() and get_all_classes() methods."""

    def test_has_registered(self) -> None:
        """has() returns True for a registered class."""
        factory = DependencyFactory((DependencyInfo(cls=_SimpleService),))
        assert factory.has(_SimpleService) is True

    def test_has_unregistered(self) -> None:
        """has() returns False for an unregistered class."""
        factory = DependencyFactory((DependencyInfo(cls=_SimpleService),))
        assert factory.has(_NoArgService) is False

    def test_get_all_classes(self) -> None:
        """get_all_classes() returns all registered dependency types."""
        factory = DependencyFactory(
            (
                DependencyInfo(cls=_SimpleService),
                DependencyInfo(cls=_NoArgService),
            )
        )

        classes = factory.get_all_classes()
        assert _SimpleService in classes
        assert _NoArgService in classes
        assert len(classes) == 2


# ═════════════════════════════════════════════════════════════════════════════
# Legacy dict format
# ═════════════════════════════════════════════════════════════════════════════


class TestLegacyDictFormat:
    """Verify backward-compatible dict-based input."""

    async def test_dict_format_accepted(self) -> None:
        """A list of dicts with 'class' keys is accepted."""
        factory = DependencyFactory(
            [
                {"class": _SimpleService, "factory": None, "description": "test"},
            ]
        )

        instance = await factory.resolve(_SimpleService)
        assert isinstance(instance, _SimpleService)

    async def test_dict_with_factory(self) -> None:
        """A dict with a factory function uses it for creation."""
        factory = DependencyFactory(
            [
                {
                    "class": _SimpleService,
                    "factory": lambda: _SimpleService(name="dict_factory"),
                    "description": "from dict",
                },
            ]
        )

        instance = await factory.resolve(_SimpleService)
        assert instance.name == "dict_factory"

    def test_dict_format_has_works(self) -> None:
        """has() works correctly with dict-format input."""
        factory = DependencyFactory(
            [
                {"class": _SimpleService, "factory": None, "description": ""},
            ]
        )

        assert factory.has(_SimpleService) is True
        assert factory.has(_NoArgService) is False


# ═════════════════════════════════════════════════════════════════════════════
# DependencyInfo frozen
# ═════════════════════════════════════════════════════════════════════════════


class TestDependencyInfoFrozen:
    """Verify DependencyInfo is immutable."""

    def test_cannot_modify_cls(self) -> None:
        """Attempting to change cls raises AttributeError."""
        info = DependencyInfo(cls=_SimpleService)

        with pytest.raises(AttributeError):
            info.cls = _NoArgService  # type: ignore[misc]

    def test_cannot_modify_description(self) -> None:
        """Attempting to change description raises AttributeError."""
        info = DependencyInfo(cls=_SimpleService, description="test")

        with pytest.raises(AttributeError):
            info.description = "other"  # type: ignore[misc]
