# tests/runtime/test_machine_nested_connections.py
"""ToolsBox._wrap_connections behavior for nested child runs."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from action_machine.resources.base_resource_manager import BaseResourceManager
from action_machine.runtime.tools_box import ToolsBox


class TestConnectionWrapping:
    """ToolsBox._wrap_connections wraps managers for child actions."""

    def test_wrap_connections_with_wrapper_class(self) -> None:
        from action_machine.resources.sql import (
            SqlConnectionManager,
            WrapperSqlConnectionManager,
        )

        mock_manager = MagicMock(spec=SqlConnectionManager)
        mock_manager.get_wrapper_class.return_value = WrapperSqlConnectionManager
        mock_manager.rollup = False

        box = ToolsBox(
            run_child=AsyncMock(),
            factory=MagicMock(),
            resources=None,
            log=MagicMock(),
            nested_level=1,
            rollup=False,
        )

        wrapped = box._wrap_connections({"db": mock_manager})

        assert wrapped is not None
        assert "db" in wrapped
        assert isinstance(wrapped["db"], WrapperSqlConnectionManager)

    def test_wrap_connections_without_wrapper_class(self) -> None:
        mock_manager = MagicMock(spec=BaseResourceManager)
        mock_manager.get_wrapper_class.return_value = None

        box = ToolsBox(
            run_child=AsyncMock(),
            factory=MagicMock(),
            resources=None,
            log=MagicMock(),
            nested_level=1,
            rollup=False,
        )

        wrapped = box._wrap_connections({"cache": mock_manager})

        assert wrapped is not None
        assert wrapped["cache"] is mock_manager

    def test_wrap_connections_none_returns_none(self) -> None:
        box = ToolsBox(
            run_child=AsyncMock(),
            factory=MagicMock(),
            resources=None,
            log=MagicMock(),
            nested_level=1,
            rollup=False,
        )

        result = box._wrap_connections(None)
        assert result is None
