# packages/aoa-action-machine/tests/action_machine/resources/test_gateway_defaults.py
"""A gateway passes to a nested action as it is, and a rollup run refuses it."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from aoa.action_machine.exceptions import RollupNotSupportedError
from aoa.action_machine.runtime.tools_box import ToolsBox
from tests.support.domain_model.services import PaymentClient, PaymentGateway


def test_a_gateway_has_no_wrapper_class() -> None:
    """A gateway holds no transaction a nested action could end."""
    assert PaymentGateway(AsyncMock(spec=PaymentClient)).get_wrapper_class() is None


def test_a_nested_action_gets_the_same_gateway() -> None:
    """The connections a child action receives hold the very gateway of its parent."""
    gateway = PaymentGateway(AsyncMock(spec=PaymentClient))
    box = object.__new__(ToolsBox)  # _wrap_connections reads no state of the box
    wrapped = box._wrap_connections({"payment": gateway})
    assert wrapped is not None
    assert wrapped["payment"] is gateway


async def test_a_rollup_run_refuses_a_gateway() -> None:
    """A call already made to a service cannot be taken back."""
    with pytest.raises(RollupNotSupportedError, match="PaymentGateway"):
        await PaymentGateway(AsyncMock(spec=PaymentClient)).check_rollup_support()


async def test_a_gateway_method_reaches_its_client() -> None:
    """An aspect calls the gateway; the gateway calls its private client."""
    client = AsyncMock(spec=PaymentClient)
    client.charge.return_value = "TXN-1"
    assert await PaymentGateway(client).charge(10.0, "EUR") == "TXN-1"
    client.charge.assert_awaited_once_with(10.0, "EUR")
