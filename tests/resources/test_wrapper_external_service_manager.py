# tests/resources/test_wrapper_external_service_manager.py
"""
Tests for WrapperExternalServiceManager — nested-action proxy for external clients.
"""

import pytest

from action_machine.resources.base_resource_manager import BaseResourceManager
from action_machine.resources.external_service import (
    ExternalServiceManager,
    ProtocolExternalServiceManager,
    WrapperExternalServiceManager,
)


@pytest.fixture
def client() -> object:
    """Arbitrary stand-in for an API/SDK client."""
    return object()


@pytest.fixture
def owner(client: object) -> ExternalServiceManager[object]:
    """Root-level external service manager."""
    return ExternalServiceManager(client)


@pytest.fixture
def wrapper(owner: ExternalServiceManager[object]) -> WrapperExternalServiceManager:
    """Single wrapper around the owner manager."""
    return WrapperExternalServiceManager(owner)


class TestConstructor:
    """Wrapper construction and identity."""

    def test_delegates_service_to_inner(
        self, wrapper: WrapperExternalServiceManager, client: object,
    ) -> None:
        """``service`` reads through to the wrapped manager’s client."""
        assert wrapper.service is client

    def test_delegates_check_rollup_support(
        self, wrapper: WrapperExternalServiceManager, owner: ExternalServiceManager[object],
    ) -> None:
        """Rollup capability matches the wrapped manager."""
        assert wrapper.check_rollup_support() == owner.check_rollup_support()
        assert wrapper.check_rollup_support() is False

    def test_is_protocol_not_external_service_manager(
        self, wrapper: WrapperExternalServiceManager,
    ) -> None:
        """Wrapper implements the protocol but is not a concrete ExternalServiceManager."""
        assert isinstance(wrapper, ProtocolExternalServiceManager)
        assert not isinstance(wrapper, ExternalServiceManager)

    def test_stores_inner_reference(
        self, wrapper: WrapperExternalServiceManager, owner: ExternalServiceManager[object],
    ) -> None:
        assert wrapper._inner is owner


class TestGetWrapperClass:
    """Re-wrapping for deeper nesting."""

    def test_returns_wrapper_class(self, wrapper: WrapperExternalServiceManager) -> None:
        result = wrapper.get_wrapper_class()
        assert result is WrapperExternalServiceManager


class TestDoubleWrapping:
    """Chained wrappers still expose the same client."""

    def test_double_wrap_same_service(
        self, owner: ExternalServiceManager[object], client: object,
    ) -> None:
        w1 = WrapperExternalServiceManager(owner)
        w2 = WrapperExternalServiceManager(w1)
        assert w2.service is client

    def test_triple_wrap_same_service(
        self, owner: ExternalServiceManager[object], client: object,
    ) -> None:
        w1 = WrapperExternalServiceManager(owner)
        w2 = WrapperExternalServiceManager(w1)
        w3 = WrapperExternalServiceManager(w2)
        assert w3.service is client


class TestWrapConnectionsIntegration:
    """Same pattern as ToolsBox._wrap_connections."""

    @staticmethod
    def _wrap_connections(connections: dict | None) -> dict | None:
        if connections is None:
            return None
        wrapped: dict[str, BaseResourceManager] = {}
        for key, connection in connections.items():
            wrapper_class = connection.get_wrapper_class()
            if wrapper_class is not None:
                wrapped[key] = wrapper_class(connection)
            else:
                wrapped[key] = connection
        return wrapped

    def test_wraps_owner_in_wrapper(
        self, owner: ExternalServiceManager[object], client: object,
    ) -> None:
        out = self._wrap_connections({"api": owner})
        assert isinstance(out["api"], WrapperExternalServiceManager)
        assert out["api"].service is client

    def test_rewraps_wrapper(
        self, wrapper: WrapperExternalServiceManager, client: object,
    ) -> None:
        out = self._wrap_connections({"api": wrapper})
        assert isinstance(out["api"], WrapperExternalServiceManager)
        assert out["api"].service is client

    def test_none_returns_none(self) -> None:
        assert self._wrap_connections(None) is None

    def test_empty_dict(self) -> None:
        assert self._wrap_connections({}) == {}
