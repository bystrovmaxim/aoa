"""
Тесты ConsoleLogger — вывода в консоль с ANSI-раскраской.

Проверяем:
- Вывод сообщений через print
- Отступы по уровню indent
- Форматирование скоупа в квадратных скобках
- ANSI-раскраску (цветной вывод)
- Обработку маркера <none>
"""

import pytest

from action_machine.Logging.console_logger import console_logger
from action_machine.Logging.log_scope import log_scope
from tests.conftest import ParamsTest, make_context


class TestConsoleLogger:
    """Тесты ConsoleLogger."""

    # ------------------------------------------------------------------
    # ТЕСТЫ: Базовый вывод (без цветов)
    # ------------------------------------------------------------------

    @pytest.mark.anyio
    async def test_write_outputs_to_stdout(self, capsys: pytest.CaptureFixture[str]):
        """write выводит сообщение через print."""
        logger = console_logger(use_colors=False)
        scope = log_scope(action="MyAction", aspect="load")
        ctx = make_context()
        params = ParamsTest()

        await logger.write(scope, "Hello world", {}, ctx, {}, params, 0)

        captured = capsys.readouterr()
        assert "[MyAction.load] Hello world" in captured.out
        assert captured.out.endswith("\n")

    @pytest.mark.anyio
    async def test_write_without_scope(self, capsys: pytest.CaptureFixture[str]):
        """write без скоупа не выводит квадратные скобки."""
        logger = console_logger(use_colors=False)
        scope = log_scope()  # пустой скоуп
        ctx = make_context()
        params = ParamsTest()

        await logger.write(scope, "No scope", {}, ctx, {}, params, 0)

        captured = capsys.readouterr()
        assert "No scope" in captured.out
        assert "[" not in captured.out
        assert "]" not in captured.out

    @pytest.mark.anyio
    async def test_write_with_empty_scope_values(self, capsys: pytest.CaptureFixture[str]):
        """write с пустыми значениями в скоупе пропускает их."""
        logger = console_logger(use_colors=False)
        scope = log_scope(action="", aspect="test", event="")
        ctx = make_context()
        params = ParamsTest()

        await logger.write(scope, "Message", {}, ctx, {}, params, 0)

        captured = capsys.readouterr()
        # Пустые значения не должны попадать в вывод
        assert "[test] Message" in captured.out or "Message" in captured.out

    # ------------------------------------------------------------------
    # ТЕСТЫ: Отступы (indent)
    # ------------------------------------------------------------------

    @pytest.mark.anyio
    async def test_write_with_indent(self, capsys: pytest.CaptureFixture[str]):
        """write добавляет отступ по уровню indent."""
        logger = console_logger(use_colors=False)
        scope = log_scope(action="MyAction")
        ctx = make_context()
        params = ParamsTest()

        await logger.write(scope, "Indented", {}, ctx, {}, params, 3)

        captured = capsys.readouterr()
        # 3 * "  " = 6 пробелов
        assert captured.out.startswith("      ")
        assert "[MyAction] Indented" in captured.out

    @pytest.mark.anyio
    async def test_write_with_zero_indent(self, capsys: pytest.CaptureFixture[str]):
        """indent=0 не добавляет отступ."""
        logger = console_logger(use_colors=False)
        scope = log_scope(action="MyAction")
        ctx = make_context()
        params = ParamsTest()

        await logger.write(scope, "No indent", {}, ctx, {}, params, 0)

        captured = capsys.readouterr()
        assert not captured.out.startswith(" ")
        assert "[MyAction] No indent" in captured.out

    @pytest.mark.anyio
    async def test_write_with_large_indent(self, capsys: pytest.CaptureFixture[str]):
        """write работает с большими значениями indent."""
        logger = console_logger(use_colors=False)
        scope = log_scope(action="MyAction")
        ctx = make_context()
        params = ParamsTest()

        await logger.write(scope, "Deep", {}, ctx, {}, params, 10)

        captured = capsys.readouterr()
        # 10 * "  " = 20 пробелов
        assert captured.out.startswith(" " * 20)

    # ------------------------------------------------------------------
    # ТЕСТЫ: Форматирование сообщения
    # ------------------------------------------------------------------

    @pytest.mark.anyio
    async def test_write_with_special_characters(self, capsys: pytest.CaptureFixture[str]):
        """write корректно выводит специальные символы."""
        logger = console_logger(use_colors=False)
        scope = log_scope(action="MyAction")
        ctx = make_context()
        params = ParamsTest()

        message = "Special: \n\t\r\\"
        await logger.write(scope, message, {}, ctx, {}, params, 0)

        captured = capsys.readouterr()
        assert message in captured.out

    @pytest.mark.anyio
    async def test_write_with_unicode(self, capsys: pytest.CaptureFixture[str]):
        """write поддерживает unicode-символы."""
        logger = console_logger(use_colors=False)
        scope = log_scope(action="MyAction")
        ctx = make_context()
        params = ParamsTest()

        message = "Привет мир! 🚀"
        await logger.write(scope, message, {}, ctx, {}, params, 0)

        captured = capsys.readouterr()
        assert message in captured.out

    # ------------------------------------------------------------------
    # ТЕСТЫ: ANSI-раскраска
    # ------------------------------------------------------------------

    @pytest.mark.anyio
    async def test_write_no_colors(self, capsys: pytest.CaptureFixture[str]):
        """write без цветов не содержит ANSI-кодов."""
        logger = console_logger(use_colors=False)
        scope = log_scope(action="MyAction")
        ctx = make_context()
        params = ParamsTest()

        await logger.write(scope, "Clean text", {}, ctx, {}, params, 0)

        captured = capsys.readouterr()
        assert "\033[" not in captured.out  # нет ANSI-кодов

    @pytest.mark.anyio
    async def test_write_with_colors_contains_ansi(self, capsys: pytest.CaptureFixture[str]):
        """write с цветами содержит ANSI-коды."""
        logger = console_logger(use_colors=True)
        scope = log_scope(action="MyAction")
        ctx = make_context()
        params = ParamsTest()

        await logger.write(scope, "Colored", {}, ctx, {}, params, 0)

        captured = capsys.readouterr()
        assert "\033[" in captured.out  # есть ANSI-коды

    @pytest.mark.anyio
    async def test_write_colorizes_none_marker(self, capsys: pytest.CaptureFixture[str]):
        """write раскрашивает <none> красным при use_colors=True."""
        logger = console_logger(use_colors=True)
        scope = log_scope(action="MyAction")
        ctx = make_context()
        params = ParamsTest()

        await logger.write(scope, "value=<none>", {}, ctx, {}, params, 0)

        captured = capsys.readouterr()
        # Проверяем наличие ANSI-кода красного цвета вокруг <none>
        assert "\033[31m<none>\033[0m" in captured.out

    @pytest.mark.anyio
    async def test_write_does_not_colorize_none_when_disabled(self, capsys: pytest.CaptureFixture[str]):
        """write не раскрашивает <none> если use_colors=False."""
        logger = console_logger(use_colors=False)
        scope = log_scope(action="MyAction")
        ctx = make_context()
        params = ParamsTest()

        await logger.write(scope, "value=<none>", {}, ctx, {}, params, 0)

        captured = capsys.readouterr()
        assert "\033[31m" not in captured.out
        assert "<none>" in captured.out

    @pytest.mark.anyio
    async def test_write_colorizes_multiple_none_markers(self, capsys: pytest.CaptureFixture[str]):
        """write раскрашивает все вхождения <none> красным."""
        logger = console_logger(use_colors=True)
        scope = log_scope(action="MyAction")
        ctx = make_context()
        params = ParamsTest()

        message = "user=<none>, role=<none>, value=<none>"
        await logger.write(scope, message, {}, ctx, {}, params, 0)

        captured = capsys.readouterr()
        # Должно быть 3 вхождения красного маркера
        assert captured.out.count("\033[31m<none>\033[0m") == 3

    # ------------------------------------------------------------------
    # ТЕСТЫ: Раскраска скоупа
    # ------------------------------------------------------------------

    @pytest.mark.anyio
    async def test_write_colorizes_scope_grey(self, capsys: pytest.CaptureFixture[str]):
        """write раскрашивает скоуп серым цветом."""
        logger = console_logger(use_colors=True)
        scope = log_scope(action="MyAction", aspect="test")
        ctx = make_context()
        params = ParamsTest()

        await logger.write(scope, "message", {}, ctx, {}, params, 0)

        captured = capsys.readouterr()
        # Проверяем серый цвет вокруг скоупа
        assert "\033[90mMyAction.test\033[0m" in captured.out

    @pytest.mark.anyio
    async def test_write_does_not_colorize_scope_when_disabled(self, capsys: pytest.CaptureFixture[str]):
        """write не раскрашивает скоуп если use_colors=False."""
        logger = console_logger(use_colors=False)
        scope = log_scope(action="MyAction")
        ctx = make_context()
        params = ParamsTest()

        await logger.write(scope, "message", {}, ctx, {}, params, 0)

        captured = capsys.readouterr()
        assert "\033[90m" not in captured.out
        assert "[MyAction] message" in captured.out

    # ------------------------------------------------------------------
    # ТЕСТЫ: Комбинация раскрасок
    # ------------------------------------------------------------------

    @pytest.mark.anyio
    async def test_write_with_scope_and_none_marker(self, capsys: pytest.CaptureFixture[str]):
        """write раскрашивает и скоуп, и маркер <none> одновременно."""
        logger = console_logger(use_colors=True)
        scope = log_scope(action="MyAction")
        ctx = make_context()
        params = ParamsTest()

        await logger.write(scope, "value=<none>", {}, ctx, {}, params, 0)

        captured = capsys.readouterr()
        # Должен быть серый скоуп и красный <none>
        assert "\033[90mMyAction\033[0m" in captured.out
        assert "\033[31m<none>\033[0m" in captured.out

    # ------------------------------------------------------------------
    # ТЕСТЫ: Разделители и формат
    # ------------------------------------------------------------------

    @pytest.mark.anyio
    async def test_write_format_with_scope(self, capsys: pytest.CaptureFixture[str]):
        """write соблюдает формат [scope] message."""
        logger = console_logger(use_colors=False)
        scope = log_scope(action="Test")
        ctx = make_context()
        params = ParamsTest()

        await logger.write(scope, "hello", {}, ctx, {}, params, 0)

        captured = capsys.readouterr()
        assert captured.out == "[Test] hello\n"

    @pytest.mark.anyio
    async def test_write_format_with_indent_and_scope(self, capsys: pytest.CaptureFixture[str]):
        """write соблюдает формат с отступом и скоупом."""
        logger = console_logger(use_colors=False)
        scope = log_scope(action="Test")
        ctx = make_context()
        params = ParamsTest()

        await logger.write(scope, "hello", {}, ctx, {}, params, 2)

        captured = capsys.readouterr()
        assert captured.out == "    [Test] hello\n"  # 2 * "  " = 4 пробела

    # ------------------------------------------------------------------
    # ТЕСТЫ: Множественные вызовы
    # ------------------------------------------------------------------

    @pytest.mark.anyio
    async def test_multiple_writes(self, capsys: pytest.CaptureFixture[str]):
        """несколько вызовов write выводят несколько строк."""
        logger = console_logger(use_colors=False)
        scope = log_scope(action="Test")
        ctx = make_context()
        params = ParamsTest()

        await logger.write(scope, "first", {}, ctx, {}, params, 0)
        await logger.write(scope, "second", {}, ctx, {}, params, 1)
        await logger.write(scope, "third", {}, ctx, {}, params, 2)

        captured = capsys.readouterr()
        lines = captured.out.strip().split("\n")
        assert len(lines) == 3
        assert lines[0] == "[Test] first"
        assert lines[1] == "  [Test] second"
        assert lines[2] == "    [Test] third"
