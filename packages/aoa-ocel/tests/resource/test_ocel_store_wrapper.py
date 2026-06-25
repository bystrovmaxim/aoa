# tests/ocel/resource/test_ocel_store_wrapper.py
"""OcelStoreWrapper (plan §5.27.2, mirrors WrapperSqlResource)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from aoa.action_machine.resources.base_resource import BaseResource
from aoa.ocel.dto.ocel_event import OcelEvent
from aoa.ocel.exceptions import OcelResourceAccessProhibitedError
from aoa.ocel.resource import InMemoryOcelStoreResource, OcelStoreResource, OcelStoreWrapper


@pytest.fixture
def inner() -> MagicMock:
    mock = MagicMock(spec=OcelStoreResource)
    mock.open = AsyncMock()
    mock.close = AsyncMock()
    mock.add_event = AsyncMock()
    mock.check_rollup_support = AsyncMock(return_value=False)
    mock.get_wrapper_class = MagicMock(return_value=OcelStoreWrapper)
    return mock


@pytest.mark.asyncio
async def test_open_raises_without_delegating(inner: MagicMock) -> None:
    wrapper = OcelStoreWrapper(inner)
    with pytest.raises(OcelResourceAccessProhibitedError, match="open is unavailable"):
        await wrapper.open()
    inner.open.assert_not_called()


@pytest.mark.asyncio
async def test_close_raises_without_delegating(inner: MagicMock) -> None:
    wrapper = OcelStoreWrapper(inner)
    with pytest.raises(OcelResourceAccessProhibitedError, match="close is unavailable"):
        await wrapper.close()
    inner.close.assert_not_called()


@pytest.mark.asyncio
async def test_add_event_delegates(inner: MagicMock) -> None:
    wrapper = OcelStoreWrapper(inner)
    event = MagicMock(spec=OcelEvent)
    await wrapper.add_event(event)
    inner.add_event.assert_awaited_once_with(event)


def test_get_wrapper_class_returns_self() -> None:
    inner = MagicMock(spec=OcelStoreResource)
    wrapper = OcelStoreWrapper(inner)
    assert wrapper.get_wrapper_class() is OcelStoreWrapper


def test_in_memory_resource_registers_wrapper_class(tmp_path) -> None:
    resource = InMemoryOcelStoreResource(output_file=tmp_path / "x.json")
    assert resource.get_wrapper_class() is OcelStoreWrapper
    assert isinstance(resource, BaseResource)


def test_tools_box_wrap_pattern(tmp_path) -> None:
    """Same contract as ToolsBox._wrap_connections: wrapper(inner)."""
    inner = InMemoryOcelStoreResource(output_file=tmp_path / "wrap.json")
    wrapper_class = inner.get_wrapper_class()
    assert wrapper_class is OcelStoreWrapper
    proxy = wrapper_class(inner)
    assert isinstance(proxy, OcelStoreWrapper)
    assert isinstance(proxy, BaseResource)
