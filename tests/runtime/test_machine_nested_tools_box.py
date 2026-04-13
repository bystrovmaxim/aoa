# tests/runtime/test_machine_nested_tools_box.py
"""ToolsBox.resolve() and read-only surface used during nested execution."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from action_machine.runtime.tools_box import ToolsBox


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
