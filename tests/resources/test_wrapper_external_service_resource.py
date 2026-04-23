# tests/resources/test_wrapper_external_service_resource.py
"""
Tests for WrapperExternalServiceResource — nested-action proxy for external clients.
"""

import pytest

from action_machine.resources.base_resource import BaseResource
from action_machine.resources.external_service import (
    ExternalServiceResource,
    ProtocolExternalServiceResource,
    WrapperExternalServiceResource,
)


@pytest.fixture
def client() -> object:
    """Arbitrary stand-in for an API/SDK client."""
    return object()


@pytest.fixture
def owner(client: object) -> ExternalServiceResource[object]:
    """Root-level external service manager."""
    return ExternalServiceResource(client)


@pytest.fixture
def wrapper(owner: ExternalServiceResource[object]) -> WrapperExternalServiceResource:
    """Single wrapper around the owner manager."""
    return WrapperExternalServiceResource(owner)


class TestConstructor:
    """Wrapper construction and identity."""

    def test_delegates_service_to_inner(
        self, wrapper: WrapperExternalServiceResource, client: object,
    ) -> None:
        """``service`` reads through to the wrapped manager’s client."""
        assert wrapper.service is client

    def test_delegates_check_rollup_support(
        self, wrapper: WrapperExternalServiceResource, owner: ExternalServiceResource[object],
    ) -> None:
        """Rollup capability matches the wrapped manager."""
        assert wrapper.check_rollup_support() == owner.check_rollup_support()
        assert wrapper.check_rollup_support() is False

    def test_is_protocol_not_external_service_resource(
        self, wrapper: WrapperExternalServiceResource,
    ) -> None:
        """Wrapper implements the protocol but is not a concrete ExternalServiceResource."""
        assert isinstance(wrapper, ProtocolExternalServiceResource)
        assert not isinstance(wrapper, ExternalServiceResource)

    def test_stores_inner_reference(
        self, wrapper: WrapperExternalServiceResource, owner: ExternalServiceResource[object],
    ) -> None:
        assert wrapper._inner is owner


class TestGetWrapperClass:
    """Re-wrapping for deeper nesting."""

    def test_returns_wrapper_class(self, wrapper: WrapperExternalServiceResource) -> None:
        result = wrapper.get_wrapper_class()
        assert result is WrapperExternalServiceResource


class TestDoubleWrapping:
    """Chained wrappers still expose the same client."""

    def test_double_wrap_same_service(
        self, owner: ExternalServiceResource[object], client: object,
    ) -> None:
        w1 = WrapperExternalServiceResource(owner)
        w2 = WrapperExternalServiceResource(w1)
        assert w2.service is client

    def test_triple_wrap_same_service(
        self, owner: ExternalServiceResource[object], client: object,
    ) -> None:
        w1 = WrapperExternalServiceResource(owner)
        w2 = WrapperExternalServiceResource(w1)
        w3 = WrapperExternalServiceResource(w2)
        assert w3.service is client


class TestWrapConnectionsIntegration:
    """Same pattern as ToolsBox._wrap_connections."""

    @staticmethod
    def _wrap_connections(connections: dict | None) -> dict | None:
        if connections is None:
            return None
        wrapped: dict[str, BaseResource] = {}
        for key, connection in connections.items():
            wrapper_class = connection.get_wrapper_class()
            if wrapper_class is not None:
                wrapped[key] = wrapper_class(connection)
            else:
                wrapped[key] = connection
        return wrapped

    def test_wraps_owner_in_wrapper(
        self, owner: ExternalServiceResource[object], client: object,
    ) -> None:
        out = self._wrap_connections({"api": owner})
        assert isinstance(out["api"], WrapperExternalServiceResource)
        assert out["api"].service is client

    def test_rewraps_wrapper(
        self, wrapper: WrapperExternalServiceResource, client: object,
    ) -> None:
        out = self._wrap_connections({"api": wrapper})
        assert isinstance(out["api"], WrapperExternalServiceResource)
        assert out["api"].service is client

    def test_none_returns_none(self) -> None:
        assert self._wrap_connections(None) is None

    def test_empty_dict(self) -> None:
        assert self._wrap_connections({}) == {}
