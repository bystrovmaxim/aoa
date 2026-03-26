# tests/logging/test_console_logger.py
"""
Tests for ConsoleLogger – output to console with indentation.

Checks:
- Messages are printed via print
- Indentation based on indent level
- No automatic scope prefix is added
- No ANSI colors are added by the logger itself (colors are handled via filters)
"""

import pytest

from action_machine.logging.console_logger import ConsoleLogger
from action_machine.logging.log_scope import LogScope
from tests.conftest import ParamsTest, make_context


class TestConsoleLogger:
    """Tests for ConsoleLogger."""

    # ------------------------------------------------------------------
    # TESTS: Basic output (no colors)
    # ------------------------------------------------------------------

    @pytest.mark.anyio
    async def test_write_outputs_to_stdout(self, capsys: pytest.CaptureFixture[str]):
        """write prints the message via print."""
        logger = ConsoleLogger(use_colors=False)
        scope = LogScope(action="MyAction", aspect="load")
        ctx = make_context()
        params = ParamsTest()

        await logger.write(scope, "Hello world", {"level": "info"}, ctx, {}, params, 0)

        captured = capsys.readouterr()
        assert "Hello world" in captured.out
        assert captured.out.endswith("\n")

    @pytest.mark.anyio
    async def test_write_with_indent(self, capsys: pytest.CaptureFixture[str]):
        """write adds indentation based on indent level."""
        logger = ConsoleLogger(use_colors=False)
        scope = LogScope(action="MyAction")
        ctx = make_context()
        params = ParamsTest()

        await logger.write(scope, "Indented", {"level": "info"}, ctx, {}, params, 3)

        captured = capsys.readouterr()
        # 3 * "  " = 6 spaces
        assert captured.out.startswith("      ")
        assert "Indented" in captured.out

    @pytest.mark.anyio
    async def test_write_without_scope(self, capsys: pytest.CaptureFixture[str]):
        """write without scope works fine (no brackets)."""
        logger = ConsoleLogger(use_colors=False)
        scope = LogScope()  # empty scope
        ctx = make_context()
        params = ParamsTest()

        await logger.write(scope, "No scope", {"level": "info"}, ctx, {}, params, 0)

        captured = capsys.readouterr()
        assert "No scope" in captured.out
        assert "[" not in captured.out
        assert "]" not in captured.out

    @pytest.mark.anyio
    async def test_write_with_special_characters(self, capsys: pytest.CaptureFixture[str]):
        """write handles special characters correctly."""
        logger = ConsoleLogger(use_colors=False)
        scope = LogScope(action="MyAction")
        ctx = make_context()
        params = ParamsTest()

        message = "Special: \n\t\r\\"
        await logger.write(scope, message, {"level": "info"}, ctx, {}, params, 0)

        captured = capsys.readouterr()
        assert message in captured.out

    # ------------------------------------------------------------------
    # TESTS: Color support (delegated to coordinator, not logger)
    # ------------------------------------------------------------------
    @pytest.mark.anyio
    async def test_write_with_colors_preserved_when_use_colors_true(self, capsys: pytest.CaptureFixture[str]):
        """When use_colors=True, ANSI codes are preserved (logger does not strip)."""
        logger = ConsoleLogger(use_colors=True)
        scope = LogScope(action="MyAction")
        ctx = make_context()
        params = ParamsTest()
        colored_message = "\033[31mred text\033[0m"

        await logger.write(scope, colored_message, {"level": "info"}, ctx, {}, params, 0)

        captured = capsys.readouterr()
        assert "\033[31m" in captured.out
        assert "red text" in captured.out

    @pytest.mark.anyio
    async def test_write_without_level_does_not_add_color(self, capsys: pytest.CaptureFixture[str]):
        """If level is absent, no color is added (logger is neutral)."""
        logger = ConsoleLogger(use_colors=True)
        scope = LogScope(action="MyAction")
        ctx = make_context()
        params = ParamsTest()

        await logger.write(scope, "Plain message", {}, ctx, {}, params, 0)

        captured = capsys.readouterr()
        assert "\033[" not in captured.out
        assert "Plain message" in captured.out

    @pytest.mark.anyio
    async def test_multiple_writes(self, capsys: pytest.CaptureFixture[str]):
        """Multiple writes produce multiple lines with correct indentation."""
        logger = ConsoleLogger(use_colors=False)
        scope = LogScope(action="Test")
        ctx = make_context()
        params = ParamsTest()

        await logger.write(scope, "first", {"level": "info"}, ctx, {}, params, 0)
        await logger.write(scope, "second", {"level": "warning"}, ctx, {}, params, 1)
        await logger.write(scope, "third", {"level": "error"}, ctx, {}, params, 2)

        captured = capsys.readouterr()
        lines = captured.out.strip().split("\n")
        assert len(lines) == 3
        assert "first" in lines[0]
        assert "  second" in lines[1]  # one indent
        assert "    third" in lines[2]  # two indents