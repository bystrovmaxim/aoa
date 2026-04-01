# tests2/logging/test_console_logger.py
"""
Тесты ConsoleLogger — вывода сообщений в консоль.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

ConsoleLogger — конкретный логгер, выводящий сообщения в stdout через print.
Поддерживает отступы на основе уровня вложенности (indent) и опциональное
сохранение ANSI-цветов.

Цвета управляются шаблонными фильтрами в координаторе; сам логгер не добавляет
автоматических ANSI-кодов, только решает, сохранять их или удалять.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

- write выводит сообщение через print.
- Поддержка отступов (indent) — сообщение сдвигается вправо.
- Настройка use_indent — включение/отключение отступов.
- Настройка indent_size — количество пробелов на один уровень.
- Поддержка цветов (use_colors) — ANSI-коды сохраняются или удаляются.
- Пустые scope и сообщения обрабатываются корректно.
"""

import pytest

from action_machine.context.context import Context
from action_machine.core.base_params import BaseParams
from action_machine.core.base_state import BaseState
from action_machine.logging.console_logger import ConsoleLogger
from action_machine.logging.log_scope import LogScope


@pytest.fixture
def empty_context() -> Context:
    """Пустой контекст для тестов."""
    return Context()


@pytest.fixture
def empty_state() -> BaseState:
    """Пустое состояние."""
    return BaseState()


@pytest.fixture
def empty_params() -> BaseParams:
    """Пустые параметры."""
    return BaseParams()


@pytest.fixture
def simple_scope() -> LogScope:
    """LogScope с action для базового вывода."""
    return LogScope(action="TestAction")


# ======================================================================
# ТЕСТЫ: Базовый вывод
# ======================================================================


class TestBasicOutput:
    """ConsoleLogger выводит сообщения через print."""

    @pytest.mark.anyio
    async def test_writes_to_stdout(
        self,
        capsys: pytest.CaptureFixture[str],
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        """
        write вызывает print, выводя сообщение в stdout.
        """
        # Arrange — логгер без цветов для простоты
        logger = ConsoleLogger(use_colors=False)

        # Act
        await logger.write(
            simple_scope, "Hello world", {"level": "info"},
            empty_context, empty_state, empty_params, indent=0,
        )

        # Assert — сообщение появилось в stdout, заканчивается переводом строки
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
        """
        Последовательные write выводят несколько строк.
        """
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

        # Assert — три строки, отступы различаются
        captured = capsys.readouterr()
        lines = captured.out.strip().split("\n")
        assert len(lines) == 3
        assert "first" in lines[0]
        assert "second" in lines[1]
        assert "third" in lines[2]


# ======================================================================
# ТЕСТЫ: Отступы
# ======================================================================


class TestIndentation:
    """ConsoleLogger добавляет отступы на основе indent."""

    @pytest.mark.anyio
    async def test_indent_adds_spaces(
        self,
        capsys: pytest.CaptureFixture[str],
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        """
        При use_indent=True и indent=3 сообщение начинается с indent * indent_size пробелов.
        По умолчанию indent_size=2, поэтому отступ = 6 пробелов.
        """
        # Arrange
        logger = ConsoleLogger(use_colors=False, use_indent=True, indent_size=2)

        # Act — indent=3 → 3*2 = 6 пробелов
        await logger.write(
            simple_scope, "Indented", {},
            empty_context, empty_state, empty_params, indent=3,
        )

        # Assert — строка начинается с 6 пробелов
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
        """
        При use_indent=False сообщение выводится без отступов, независимо от indent.
        """
        # Arrange
        logger = ConsoleLogger(use_colors=False, use_indent=False)

        # Act — indent=5, но отступы выключены
        await logger.write(
            simple_scope, "No indent", {},
            empty_context, empty_state, empty_params, indent=5,
        )

        # Assert — строка не начинается с пробелов
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
        """
        indent_size задаёт количество пробелов на один уровень.
        indent=2, indent_size=4 → 8 пробелов.
        """
        # Arrange
        logger = ConsoleLogger(use_colors=False, use_indent=True, indent_size=4)

        # Act — indent=2 → 2*4 = 8 пробелов
        await logger.write(
            simple_scope, "Deep indent", {},
            empty_context, empty_state, empty_params, indent=2,
        )

        # Assert
        captured = capsys.readouterr()
        assert captured.out.startswith("        ")
        assert "Deep indent" in captured.out


# ======================================================================
# ТЕСТЫ: Цвета
# ======================================================================


class TestColors:
    """
    ConsoleLogger сохраняет или удаляет ANSI-коды в зависимости от use_colors.

    Само добавление цветов происходит в координаторе через шаблонные фильтры.
    Логгер только решает, сохранять их или нет.
    """

    @pytest.mark.anyio
    async def test_preserves_ansi_codes_when_use_colors_true(
        self,
        capsys: pytest.CaptureFixture[str],
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        """
        use_colors=True → ANSI-коды сохраняются в выводе.
        """
        # Arrange
        logger = ConsoleLogger(use_colors=True)
        colored_message = "\033[31mred text\033[0m"

        # Act
        await logger.write(
            simple_scope, colored_message, {},
            empty_context, empty_state, empty_params, indent=0,
        )

        # Assert — ANSI-коды присутствуют
        captured = capsys.readouterr()
        assert "\033[31m" in captured.out
        assert "red text" in captured.out
        assert "\033[0m" in captured.out

    @pytest.mark.anyio
    async def test_strips_ansi_codes_when_use_colors_false(
        self,
        capsys: pytest.CaptureFixture[str],
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        """
        use_colors=False → ANSI-коды удаляются перед выводом.
        """
        # Arrange
        logger = ConsoleLogger(use_colors=False)
        colored_message = "\033[31mred text\033[0m"

        # Act
        await logger.write(
            simple_scope, colored_message, {},
            empty_context, empty_state, empty_params, indent=0,
        )

        # Assert — ANSI-коды отсутствуют, текст остался
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
        """
        Свойство supports_colors отражает значение use_colors.
        LogCoordinator использует это свойство, чтобы решить, вызывать ли strip_ansi_codes.
        """
        # Arrange & Act
        logger_true = ConsoleLogger(use_colors=True)
        logger_false = ConsoleLogger(use_colors=False)

        # Assert
        assert logger_true.supports_colors is True
        assert logger_false.supports_colors is False


# ======================================================================
# ТЕСТЫ: Граничные случаи
# ======================================================================


class TestEdgeCases:
    """Обработка пустых значений и отсутствия scope."""

    @pytest.mark.anyio
    async def test_empty_message(
        self,
        capsys: pytest.CaptureFixture[str],
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        """
        Пустое сообщение выводится как пустая строка (с отступом).
        """
        # Arrange
        logger = ConsoleLogger(use_colors=False)

        # Act
        await logger.write(
            simple_scope, "", {},
            empty_context, empty_state, empty_params, indent=0,
        )

        # Assert — пустая строка с переводом
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
        """
        LogScope может быть пустым — это не влияет на вывод.
        """
        # Arrange
        logger = ConsoleLogger(use_colors=False)
        empty_scope = LogScope()

        # Act
        await logger.write(
            empty_scope, "No scope", {},
            empty_context, empty_state, empty_params, indent=0,
        )

        # Assert — сообщение выведено без скобок, как есть
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
        """
        Специальные символы (табуляция, перенос строки, обратный слэш)
        выводятся как есть.
        """
        # Arrange
        logger = ConsoleLogger(use_colors=False)
        message = "Special: \n\t\r\\"

        # Act
        await logger.write(
            simple_scope, message, {},
            empty_context, empty_state, empty_params, indent=0,
        )

        # Assert — специальные символы присутствуют
        captured = capsys.readouterr()
        assert "Special:" in captured.out
        assert "\n" in captured.out
        assert "\t" in captured.out