# tests/intents/logging/test_console_logger.py
"""ConsoleLogger tests - outputting messages to the console.

═══════════════════ ════════════════════ ════════════════════ ════════════════════
PURPOSE
═══════════════════ ════════════════════ ════════════════════ ════════════════════

ConsoleLogger is a specific logger that outputs messages to stdout via print.
Supports indentation based on nesting level (indent) and optional
saving ANSI colors.

With ``use_colors=True`` and a non-ANSI message, the logger wraps the string in
truecolor by ``var["level"].mask``; explicit escapes in the text disable this wrapper.

═══════════════════ ════════════════════ ════════════════════ ════════════════════
SCENARIOS COVERED
═══════════════════ ════════════════════ ════════════════════ ════════════════════

- write displays a message via print.
- Indent support (indent) - the message is shifted to the right.
- Setting use_indent - enable/disable indentation.
- Setting indent_size - the number of spaces per level.
- Support for colors (use_colors) - saving/removing ANSI and auto-truecolor by level.
- Empty scope and messages are processed correctly."""

import pytest

from aoa.action_machine.context.context import Context
from aoa.action_machine.logging.channel import Channel, channel_mask_label
from aoa.action_machine.logging.console_logger import (
    DEFAULT_LEVEL_FG_PREFIX,
    ConsoleLogger,
)
from aoa.action_machine.logging.level import Level, level_label
from aoa.action_machine.logging.log_scope import LogScope
from aoa.action_machine.logging.log_var_payloads import LogChannelPayload, LogLevelPayload
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.base_state import BaseState


def _write_var(
    level: Level,
    *,
    channels: Channel | None = None,
) -> dict:
    ch = Channel.debug if channels is None else channels
    return {
        "level": LogLevelPayload(mask=level, name=level_label(level)),
        "channels": LogChannelPayload(mask=ch, names=channel_mask_label(ch)),
        "domain": None,
        "domain_name": None,
    }


@pytest.fixture
def empty_context() -> Context:
    """Empty context for tests."""
    return Context()


@pytest.fixture
def empty_state() -> BaseState:
    """Empty state."""
    return BaseState()


@pytest.fixture
def empty_params() -> BaseParams:
    """Empty parameters."""
    return BaseParams()


@pytest.fixture
def simple_scope() -> LogScope:
    """LogScope with action for basic output."""
    return LogScope(action="TestAction")


# ======================================================================
#TESTS: Basic output
# ======================================================================


class TestBasicOutput:
    """ConsoleLogger outputs messages via print."""

    @pytest.mark.anyio
    async def test_writes_to_stdout(
        self,
        capsys: pytest.CaptureFixture[str],
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        """write calls print, printing a message to stdout."""
        #Arrange - logger without colors for simplicity
        logger = ConsoleLogger(use_colors=False)

        # Act
        await logger.write(
            simple_scope,
            "Hello world",
            _write_var(Level.info),
            empty_context,
            empty_state,
            empty_params,
            indent=0,
        )

        #Assert - the message appeared in stdout, ends with a line feed
        captured = capsys.readouterr()
        assert "Hello world" in captured.out
        assert captured.out.endswith("\n")

    @pytest.mark.anyio
    async def test_multiple_writes(
        self,
        capsys: pytest.CaptureFixture[str],
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        """Consecutive write outputs multiple lines."""
        # Arrange
        logger = ConsoleLogger(use_colors=False)

        # Act
        await logger.write(
            simple_scope, "first", {}, empty_context, empty_state, empty_params, 0,
        )
        await logger.write(
            simple_scope, "second", {}, empty_context, empty_state, empty_params, 1,
        )
        await logger.write(
            simple_scope, "third", {}, empty_context, empty_state, empty_params, 2,
        )

        #Assert - three lines, indentations vary
        captured = capsys.readouterr()
        lines = captured.out.strip().split("\n")
        assert len(lines) == 3
        assert "first" in lines[0]
        assert "second" in lines[1]
        assert "third" in lines[2]


# ======================================================================
#TESTS: Indentation
# ======================================================================


class TestIndentation:
    """ConsoleLogger adds indentation based on indent."""

    @pytest.mark.anyio
    async def test_indent_adds_spaces(
        self,
        capsys: pytest.CaptureFixture[str],
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        """With use_indent=True and indent=3, the message begins with indent * indent_size spaces.
        By default indent_size=2, so indent = 6 spaces."""
        # Arrange
        logger = ConsoleLogger(use_colors=False, use_indent=True, indent_size=2)

        #Act - indent=3 → 3*2 = 6 spaces
        await logger.write(
            simple_scope, "Indented", {},
            empty_context, empty_state, empty_params, indent=3,
        )

        #Assert - line starts with 6 spaces
        captured = capsys.readouterr()
        assert captured.out.startswith("      ")
        assert "Indented" in captured.out

    @pytest.mark.anyio
    async def test_no_indent_when_disabled(
        self,
        capsys: pytest.CaptureFixture[str],
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        """When use_indent=False, the message is displayed without indentation, regardless of indent."""
        # Arrange
        logger = ConsoleLogger(use_colors=False, use_indent=False)

        #Act — indent=5, but indents are disabled
        await logger.write(
            simple_scope, "No indent", {},
            empty_context, empty_state, empty_params, indent=5,
        )

        #Assert - the line does not start with spaces
        captured = capsys.readouterr()
        assert captured.out.startswith("No indent")

    @pytest.mark.anyio
    async def test_custom_indent_size(
        self,
        capsys: pytest.CaptureFixture[str],
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        """indent_size specifies the number of spaces per level.
        indent=2, indent_size=4 → 8 spaces."""
        # Arrange
        logger = ConsoleLogger(use_colors=False, use_indent=True, indent_size=4)

        #Act - indent=2 → 2*4 = 8 spaces
        await logger.write(
            simple_scope, "Deep indent", {},
            empty_context, empty_state, empty_params, indent=2,
        )

        # Assert
        captured = capsys.readouterr()
        assert captured.out.startswith("        ")
        assert "Deep indent" in captured.out


# ======================================================================
#TESTS: Colors
# ======================================================================


class TestColors:
    """ConsoleLogger saves or removes ANSI codes depending on use_colors.

    With ``LogLevelPayload`` in ``var["level"]`` the whole line gets the base truecolor
    level; explicit escapes
    in the template are saved, after ``\\033[0m`` the base color is again substituted."""

    @pytest.mark.anyio
    async def test_preserves_ansi_codes_when_use_colors_true(
        self,
        capsys: pytest.CaptureFixture[str],
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        """use_colors=True → ANSI codes are preserved in the output."""
        # Arrange
        logger = ConsoleLogger(use_colors=True)
        colored_message = "\033[31mred text\033[0m"

        # Act
        await logger.write(
            simple_scope, colored_message, {},
            empty_context, empty_state, empty_params, indent=0,
        )

        #Assert - without level in var the basic coloring is not enabled
        captured = capsys.readouterr()
        assert "\033[31m" in captured.out
        assert "red text" in captured.out
        assert "\033[0m" in captured.out
        assert "\033[38;2;" not in captured.out

    @pytest.mark.anyio
    async def test_strips_ansi_codes_when_use_colors_false(
        self,
        capsys: pytest.CaptureFixture[str],
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        """use_colors=False → ANSI codes are removed before output."""
        # Arrange
        logger = ConsoleLogger(use_colors=False)
        colored_message = "\033[31mred text\033[0m"

        # Act
        await logger.write(
            simple_scope, colored_message, {},
            empty_context, empty_state, empty_params, indent=0,
        )

        #Assert - there are no ANSI codes, the text remains
        captured = capsys.readouterr()
        assert "\033[31m" not in captured.out
        assert "red text" in captured.out
        assert "\033[0m" not in captured.out

    @pytest.mark.anyio
    async def test_supports_colors_property(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        """The supports_colors property reflects the use_colors value.
        LogCoordinator uses this property to decide whether to call strip_ansi_codes."""
        # Arrange & Act
        logger_true = ConsoleLogger(use_colors=True)
        logger_false = ConsoleLogger(use_colors=False)

        # Assert
        assert logger_true.supports_colors is True
        assert logger_false.supports_colors is False

    @pytest.mark.parametrize("level", [Level.info, Level.warning, Level.critical])
    @pytest.mark.anyio
    async def test_auto_truecolor_wraps_plain_message_by_level(
        self,
        capsys: pytest.CaptureFixture[str],
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
        level: Level,
    ) -> None:
        """Non-ANSI text gets a truecolor wrapper by level."""
        logger = ConsoleLogger(use_colors=True)
        var = _write_var(level)
        await logger.write(
            simple_scope, "plain", var, empty_context, empty_state, empty_params, 0,
        )
        out = capsys.readouterr().out
        assert DEFAULT_LEVEL_FG_PREFIX[level] in out
        assert "plain" in out
        assert "\033[0m" in out
        assert out.endswith("\n")

    @pytest.mark.anyio
    async def test_level_fg_prefixes_override(
        self,
        capsys: pytest.CaptureFixture[str],
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        """level_fg_prefixes overrides default prefixes (merge)."""
        logger = ConsoleLogger(
            use_colors=True,
            level_fg_prefixes={Level.info: "\033[32m"},
        )
        var = _write_var(Level.info)
        await logger.write(
            simple_scope, "hi", var, empty_context, empty_state, empty_params, 0,
        )
        out = capsys.readouterr().out
        assert "\033[32m" in out
        assert DEFAULT_LEVEL_FG_PREFIX[Level.info] not in out

    @pytest.mark.anyio
    async def test_auto_truecolor_wraps_indent_inside_color(
        self,
        capsys: pytest.CaptureFixture[str],
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        """The indentation is included in the wrapper: the line starts with escape, not with spaces."""
        logger = ConsoleLogger(use_colors=True, indent_size=2)
        var = _write_var(Level.warning)
        await logger.write(
            simple_scope, "x", var, empty_context, empty_state, empty_params, indent=2,
        )
        out = capsys.readouterr().out
        assert out.startswith(DEFAULT_LEVEL_FG_PREFIX[Level.warning])
        assert "    x" in out

    @pytest.mark.anyio
    async def test_base_level_restored_after_explicit_reset(
        self,
        capsys: pytest.CaptureFixture[str],
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        """After an explicit span and \\033[0m the tail is back in the level's base color."""
        logger = ConsoleLogger(use_colors=True)
        base = DEFAULT_LEVEL_FG_PREFIX[Level.info]
        var = _write_var(Level.info)
        msg = "before \033[31mRED\033[0m after"
        await logger.write(
            simple_scope, msg, var, empty_context, empty_state, empty_params, 0,
        )
        out = capsys.readouterr().out
        assert out.startswith(base)
        assert "\033[31mRED\033[0m" in out
        #immediately after resetting the explicit red again the base truecolor
        assert f"\033[0m{base} after" in out
        assert out.endswith("\033[0m\n")


# ======================================================================
#TESTS: Boundary Cases
# ======================================================================


class TestEdgeCases:
    """Handling empty values ​​and lack of scope."""

    @pytest.mark.anyio
    async def test_empty_message(
        self,
        capsys: pytest.CaptureFixture[str],
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        """An empty message is displayed as an empty line (indented)."""
        # Arrange
        logger = ConsoleLogger(use_colors=False)

        # Act
        await logger.write(
            simple_scope, "", {},
            empty_context, empty_state, empty_params, indent=0,
        )

        #Assert - empty string with translation
        captured = capsys.readouterr()
        assert captured.out == "\n"

    @pytest.mark.anyio
    async def test_empty_scope(
        self,
        capsys: pytest.CaptureFixture[str],
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        """LogScope can be empty - this does not affect the output."""
        # Arrange
        logger = ConsoleLogger(use_colors=False)
        empty_scope = LogScope()

        # Act
        await logger.write(
            empty_scope, "No scope", {},
            empty_context, empty_state, empty_params, indent=0,
        )

        #Assert - the message is displayed without parentheses, as is
        captured = capsys.readouterr()
        assert "No scope" in captured.out
        assert "[" not in captured.out

    @pytest.mark.anyio
    async def test_special_characters(
        self,
        capsys: pytest.CaptureFixture[str],
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        """Special characters (tab, line break, backslash)
        are displayed as is."""
        # Arrange
        logger = ConsoleLogger(use_colors=False)
        message = "Special: \n\t\r\\"

        # Act
        await logger.write(
            simple_scope, message, {},
            empty_context, empty_state, empty_params, indent=0,
        )

        #Assert - special characters are present
        captured = capsys.readouterr()
        assert "Special:" in captured.out
        assert "\n" in captured.out
        assert "\t" in captured.out
        assert "\t" in captured.out
