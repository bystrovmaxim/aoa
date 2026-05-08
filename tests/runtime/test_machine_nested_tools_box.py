# tests/runtime/test_machine_nested_tools_box.py
"""ToolsBox.resolve() and read-only surface used during nested execution."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from action_machine.logging.channel import Channel
from action_machine.runtime.tools_box import ToolsBox
from tests.scenarios.domain_model.child_action import ChildAction


class TestToolsBoxResolve:
    """ToolsBox.resolve() checks resources, then factory."""

    def test_resolve_from_resources_first(self) -> None:
        mock_service = MagicMock()
        mock_factory = MagicMock()

        box = ToolsBox(
            run_child=AsyncMock(),
            factory=mock_factory,
            resources={str: mock_service},
            log=MagicMock(),
            nested_level=1,
            rollup=False,
        )

        result = box.resolve(str)

        assert result is mock_service
        mock_factory.resolve.assert_not_called()

    def test_resolve_falls_through_to_factory(self) -> None:
        mock_factory = MagicMock()
        mock_factory.resolve.return_value = "factory_result"

        box = ToolsBox(
            run_child=AsyncMock(),
            factory=mock_factory,
            resources=None,
            log=MagicMock(),
            nested_level=1,
            rollup=False,
        )

        result = box.resolve(str, "arg1", key="val")

        mock_factory.resolve.assert_called_once_with(str, "arg1", rollup=False, key="val")
        assert result == "factory_result"

    def test_resolve_passes_rollup_to_factory(self) -> None:
        mock_factory = MagicMock()
        mock_factory.resolve.return_value = "result"

        box = ToolsBox(
            run_child=AsyncMock(),
            factory=mock_factory,
            resources=None,
            log=MagicMock(),
            nested_level=1,
            rollup=True,
        )

        box.resolve(str)

        mock_factory.resolve.assert_called_once_with(str, rollup=True)


class TestToolsBoxProperties:
    """Read-only ToolsBox fields used by aspects."""

    def test_nested_level_property(self) -> None:
        box = ToolsBox(
            run_child=AsyncMock(),
            factory=MagicMock(),
            resources=None,
            log=MagicMock(),
            nested_level=3,
            rollup=False,
        )
        assert box.nested_level == 3

    def test_rollup_property(self) -> None:
        box = ToolsBox(
            run_child=AsyncMock(),
            factory=MagicMock(),
            resources=None,
            log=MagicMock(),
            nested_level=1,
            rollup=True,
        )
        assert box.rollup is True

    def test_context_not_accessible(self) -> None:
        box = ToolsBox(
            run_child=AsyncMock(),
            factory=MagicMock(),
            resources=None,
            log=MagicMock(),
            nested_level=1,
            rollup=False,
        )

        assert not hasattr(box, "context")


class TestToolsBoxLoggingDelegates:
    """info / warning / critical forward to the embedded ScopedLogger."""

    @pytest.mark.asyncio
    async def test_info_warning_critical_delegate_to_log(self) -> None:
        mock_log = AsyncMock()
        box = ToolsBox(
            run_child=AsyncMock(),
            factory=MagicMock(),
            resources=None,
            log=mock_log,
            nested_level=1,
            rollup=False,
        )
        ch = Channel.business
        await box.info(ch, "i", extra=1)
        await box.warning(ch, "w")
        await box.critical(ch, "c", key="v")
        mock_log.info.assert_awaited_once_with(ch, "i", extra=1)
        mock_log.warning.assert_awaited_once_with(ch, "w")
        mock_log.critical.assert_awaited_once_with(ch, "c", key="v")


@pytest.mark.asyncio
async def test_run_instantiates_action_and_calls_run_child() -> None:
    mock_result = ChildAction.Result(processed="ok")
    run_child = AsyncMock(return_value=mock_result)

    box = ToolsBox(
        run_child=run_child,
        factory=MagicMock(),
        resources=None,
        log=MagicMock(),
        nested_level=1,
        rollup=False,
    )

    params = ChildAction.Params(value="x")
    await box.run(ChildAction, params=params, connections=None)

    run_child.assert_awaited_once()
    forwarded = run_child.call_args.kwargs
    assert isinstance(forwarded["action"], ChildAction)
    assert forwarded["params"] == params
    assert forwarded["connections"] is None
