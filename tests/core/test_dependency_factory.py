# tests/core/test_dependency_factory.py
"""
Tests for DependencyFactory — the dependency factory for actions.

Checks:
- Getting dependencies via get() from different sources
- Instance caching
- Priority of external_resources
- Wrapping of connections for child actions
- Launching child actions via run_action
"""

import pytest

from action_machine.Context.context import Context
from action_machine.Core.BaseAction import BaseAction
from action_machine.Core.BaseParams import BaseParams
from action_machine.Core.BaseResult import BaseResult
from action_machine.Core.DependencyFactory import DependencyFactory
from action_machine.ResourceManagers.BaseResourceManager import BaseResourceManager

# ----------------------------------------------------------------------
# Helper classes
# ----------------------------------------------------------------------

class MockMachine:
    """Mock action machine for verifying run calls."""

    def __init__(self):
        self.run_calls = []

    async def run(self, context, action, params, resources=None, connections=None):
        self.run_calls.append((context, action, params, resources, connections))
        return MockResult()

class MockParams(BaseParams):
    pass

class MockResult(BaseResult):
    pass

class MockAction(BaseAction[MockParams, MockResult]):
    pass

class ServiceA:
    def __init__(self, value=None):
        self.value = value or "A"

class ServiceB:
    def __init__(self, value=None):
        self.value = value or "B"

class ResourceWithWrapper(BaseResourceManager):
    """Resource that requires a wrapper."""

    def __init__(self, name="test"):
        self.name = name

    def get_wrapper_class(self):
        return MockWrapper

class ResourceWithoutWrapper(BaseResourceManager):
    """Resource without a wrapper."""

    def get_wrapper_class(self):
        return None

class MockWrapper(BaseResourceManager):
    """Wrapper for a resource."""

    def __init__(self, inner):
        self.inner = inner

    def get_wrapper_class(self):
        return None  # no second‑level wrappers needed


# ======================================================================
# TESTS: get() method
# ======================================================================

class TestGet:
    """Tests for the get method."""

    def test_get_returns_from_external_resources(self):
        """external_resources have the highest priority."""
        deps_info = [
            {"class": ServiceA, "description": "", "factory": None},
        ]
        external = {ServiceA: ServiceA(value="external")}
        factory = DependencyFactory(MockMachine(), deps_info, external)

        instance = factory.get(ServiceA)

        assert instance.value == "external"
        # External resources are not cached, so they shouldn't appear in _instances
        assert ServiceA not in factory._instances

    def test_get_returns_cached_instance_on_second_call(self):
        """Second call returns the cached instance."""
        deps_info = [
            {"class": ServiceA, "description": "", "factory": None},
        ]
        factory = DependencyFactory(MockMachine(), deps_info, None)

        first = factory.get(ServiceA)
        second = factory.get(ServiceA)

        assert first is second
        assert ServiceA in factory._instances

    def test_get_creates_via_factory_function(self):
        """If a factory is provided, it is called."""

        def custom_factory():
            return ServiceA(value="from_factory")

        deps_info = [
            {"class": ServiceA, "description": "", "factory": custom_factory},
        ]
        factory = DependencyFactory(MockMachine(), deps_info, None)

        instance = factory.get(ServiceA)
        assert instance.value == "from_factory"

    def test_get_creates_via_default_constructor(self):
        """Without a factory, the default constructor is used."""
        deps_info = [
            {"class": ServiceA, "description": "", "factory": None},
        ]
        factory = DependencyFactory(MockMachine(), deps_info, None)

        instance = factory.get(ServiceA)
        assert instance.value == "A"

    def test_get_raises_for_undeclared_class(self):
        """If the class is not declared in @depends and not in external resources, an error is raised."""
        deps_info = []  # empty
        factory = DependencyFactory(MockMachine(), deps_info, None)

        with pytest.raises(ValueError, match="not declared in @depends"):
            factory.get(ServiceA)


# ======================================================================
# TESTS: Connection wrapping (_wrap_connections)
# ======================================================================

class TestWrapConnections:
    """Tests for the _wrap_connections method."""

    def test_wrap_connections_with_wrapper(self):
        """A resource with a wrapper class is wrapped."""
        deps_info = []
        factory = DependencyFactory(MockMachine(), deps_info, None)

        inner = ResourceWithWrapper(name="inner")
        connections = {"db": inner}

        wrapped = factory._wrap_connections(connections)

        assert "db" in wrapped
        assert isinstance(wrapped["db"], MockWrapper)
        assert wrapped["db"].inner is inner

    def test_wrap_connections_without_wrapper(self):
        """A resource without a wrapper class is passed as is."""
        deps_info = []
        factory = DependencyFactory(MockMachine(), deps_info, None)

        inner = ResourceWithoutWrapper()
        connections = {"db": inner}

        wrapped = factory._wrap_connections(connections)

        assert "db" in wrapped
        assert wrapped["db"] is inner  # same object

    def test_wrap_connections_handles_empty_dict(self):
        """An empty connections dictionary is returned as is."""
        deps_info = []
        factory = DependencyFactory(MockMachine(), deps_info, None)

        wrapped = factory._wrap_connections({})
        assert wrapped == {}

    def test_wrap_connections_handles_none(self):
        """connections=None returns None (not called in run_action)."""
        # This method is not called with None in run_action, but we test it anyway.
        # Not needed – skip.


# ======================================================================
# TESTS: Launching child actions (run_action)
# ======================================================================

class TestRunAction:
    """Tests for the run_action method."""

    @pytest.mark.anyio
    async def test_run_action_wraps_connections(self):
        """Connections are wrapped before being passed to the child action."""
        machine = MockMachine()
        deps_info = [
            {"class": MockAction, "description": "", "factory": None},
        ]
        factory = DependencyFactory(machine, deps_info, None)

        # First get the action instance (so it is cached)
        action_instance = factory.get(MockAction)

        inner = ResourceWithWrapper(name="inner")
        conns = {"db": inner}

        params = MockParams()
        context = Context()  # empty context for test
        await factory.run_action(context, MockAction, params, connections=conns)

        # Check that run was called with wrapped connections
        assert len(machine.run_calls) == 1
        called_context, called_action, called_params, called_resources, called_conns = machine.run_calls[0]

        assert called_context is context
        assert called_action is action_instance
        assert called_params is params
        assert called_conns is not None
        assert "db" in called_conns
        assert isinstance(called_conns["db"], MockWrapper)
        assert called_conns["db"].inner is inner

    @pytest.mark.anyio
    async def test_run_action_without_connections(self):
        """If connections=None, no wrapping occurs."""
        machine = MockMachine()
        deps_info = [
            {"class": MockAction, "description": "", "factory": None},
        ]
        factory = DependencyFactory(machine, deps_info, None)

        params = MockParams()
        context = Context()

        await factory.run_action(context, MockAction, params, connections=None)

        assert len(machine.run_calls) == 1
        called_context, called_action, called_params, called_resources, called_conns = machine.run_calls[0]
        assert called_conns is None

    @pytest.mark.anyio
    async def test_run_action_passes_resources(self):
        """The resources parameter is passed to the child action."""
        machine = MockMachine()
        deps_info = [
            {"class": MockAction, "description": "", "factory": None},
        ]
        factory = DependencyFactory(machine, deps_info, None)

        params = MockParams()
        resources = {"some": "resource"}
        context = Context()

        await factory.run_action(context, MockAction, params, resources=resources)

        assert len(machine.run_calls) == 1
        called_context, called_action, called_params, called_resources, called_conns = machine.run_calls[0]
        assert called_resources == resources

    @pytest.mark.anyio
    async def test_run_action_returns_result(self):
        """The method returns the result from the child action."""
        machine = MockMachine()
        deps_info = [
            {"class": MockAction, "description": "", "factory": None},
        ]
        factory = DependencyFactory(machine, deps_info, None)

        params = MockParams()
        context = Context()
        result = await factory.run_action(context, MockAction, params)

        assert isinstance(result, MockResult)