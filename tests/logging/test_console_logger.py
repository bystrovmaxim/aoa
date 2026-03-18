# tests/logging/test_console_logger.py
"""
Тесты ConsoleLogger — вывода в консоль с ANSI-раскраской.

Проверяем:
- Вывод сообщений через print
- Отступы по уровню indent
- Форматирование скоупа в квадратных скобках
- ANSI-раскраску (цветной вывод)
- Обработку маркера <none>
- Раскраску в зависимости от уровня логирования (info, warning, error, debug)
"""

import pytest

from action_machine.Logging.console_logger import ConsoleLogger
from action_machine.Logging.log_scope import LogScope
from tests.conftest import ParamsTest, make_context


class TestConsoleLogger:
    """Тесты ConsoleLogger."""

    # ------------------------------------------------------------------
    # ТЕСТЫ: Базовый вывод (без цветов)
    # ------------------------------------------------------------------

    @pytest.mark.anyio
    async def test_write_outputs_to_stdout(self, capsys: pytest.CaptureFixture[str]):
        """write выводит сообщение через print."""
        logger = ConsoleLogger(use_colors=False)
        scope = LogScope(action="MyAction", aspect="load")
        ctx = make_context()
        params = ParamsTest()

        await logger.write(scope, "Hello world", {"level": "info"}, ctx, {}, params, 0)

        captured = capsys.readouterr()
        assert "[MyAction.load] Hello world" in captured.out
        assert captured.out.endswith("\n")

    @pytest.mark.anyio
    async def test_write_without_scope(self, capsys: pytest.CaptureFixture[str]):
        """write без скоупа не выводит квадратные скобки."""
        logger = ConsoleLogger(use_colors=False)
        scope = LogScope()  # пустой скоуп
        ctx = make_context()
        params = ParamsTest()

        await logger.write(scope, "No scope", {"level": "info"}, ctx, {}, params, 0)

        captured = capsys.readouterr()
        assert "No scope" in captured.out
        assert "[" not in captured.out
        assert "]" not in captured.out

    # ------------------------------------------------------------------
    # ТЕСТЫ: Отступы (indent)
    # ------------------------------------------------------------------

    @pytest.mark.anyio
    async def test_write_with_indent(self, capsys: pytest.CaptureFixture[str]):
        """write добавляет отступ по уровню indent."""
        logger = ConsoleLogger(use_colors=False)
        scope = LogScope(action="MyAction")
        ctx = make_context()
        params = ParamsTest()

        await logger.write(scope, "Indented", {"level": "info"}, ctx, {}, params, 3)

        captured = capsys.readouterr()
        # 3 * "  " = 6 пробелов
        assert captured.out.startswith("      ")
        assert "[MyAction] Indented" in captured.out

    # ------------------------------------------------------------------
    # ТЕСТЫ: Форматирование сообщения
    # ------------------------------------------------------------------

    @pytest.mark.anyio
    async def test_write_with_special_characters(self, capsys: pytest.CaptureFixture[str]):
        """write корректно выводит специальные символы."""
        logger = ConsoleLogger(use_colors=False)
        scope = LogScope(action="MyAction")
        ctx = make_context()
        params = ParamsTest()

        message = "Special: \n\t\r\\"
        await logger.write(scope, message, {"level": "info"}, ctx, {}, params, 0)

        captured = capsys.readouterr()
        assert message in captured.out

    # ------------------------------------------------------------------
    # ТЕСТЫ: ANSI-раскраска (без уровней, только <none>)
    # ------------------------------------------------------------------

    @pytest.mark.anyio
    async def test_write_no_colors(self, capsys: pytest.CaptureFixture[str]):
        """write без цветов не содержит ANSI-кодов."""
        logger = ConsoleLogger(use_colors=False)
        scope = LogScope(action="MyAction")
        ctx = make_context()
        params = ParamsTest()

        await logger.write(scope, "Clean text", {"level": "info"}, ctx, {}, params, 0)

        captured = capsys.readouterr()
        assert "\033[" not in captured.out

    @pytest.mark.anyio
    async def test_write_with_colors_contains_ansi(self, capsys: pytest.CaptureFixture[str]):
        """write с цветами содержит ANSI-коды."""
        logger = ConsoleLogger(use_colors=True)
        scope = LogScope(action="MyAction")
        ctx = make_context()
        params = ParamsTest()

        await logger.write(scope, "Colored", {"level": "info"}, ctx, {}, params, 0)

        captured = capsys.readouterr()
        assert "\033[" in captured.out

    @pytest.mark.anyio
    async def test_write_colorizes_none_marker(self, capsys: pytest.CaptureFixture[str]):
        """write раскрашивает <none> красным при use_colors=True."""
        logger = ConsoleLogger(use_colors=True)
        scope = LogScope(action="MyAction")
        ctx = make_context()
        params = ParamsTest()

        await logger.write(scope, "value=<none>", {"level": "info"}, ctx, {}, params, 0)

        captured = capsys.readouterr()
        # Проверяем наличие ANSI-кода красного цвета вокруг <none>
        assert "\033[31m<none>\033[0m" in captured.out

    # ------------------------------------------------------------------
    # ТЕСТЫ: Раскраска скоупа
    # ------------------------------------------------------------------

    @pytest.mark.anyio
    async def test_write_colorizes_scope_grey(self, capsys: pytest.CaptureFixture[str]):
        """write раскрашивает скоуп серым цветом."""
        logger = ConsoleLogger(use_colors=True)
        scope = LogScope(action="MyAction", aspect="test")
        ctx = make_context()
        params = ParamsTest()

        await logger.write(scope, "message", {"level": "info"}, ctx, {}, params, 0)

        captured = capsys.readouterr()
        # Проверяем серый цвет вокруг скоупа
        assert "\033[90mMyAction.test\033[0m" in captured.out

    # ------------------------------------------------------------------
    # ТЕСТЫ: Раскраска по уровням логирования
    # ------------------------------------------------------------------

    @pytest.mark.anyio
    async def test_write_info_level_green(self, capsys: pytest.CaptureFixture[str]):
        """Уровень info окрашивает сообщение в зелёный."""
        logger = ConsoleLogger(use_colors=True)
        scope = LogScope(action="MyAction")
        ctx = make_context()
        params = ParamsTest()

        await logger.write(scope, "Info message", {"level": "info"}, ctx, {}, params, 0)

        captured = capsys.readouterr()
        # Зелёный цвет вокруг сообщения, но не скоупа
        assert "\033[32mInfo message\033[0m" in captured.out
        assert "\033[90mMyAction\033[0m" in captured.out  # скоуп серый

    @pytest.mark.anyio
    async def test_write_warning_level_yellow(self, capsys: pytest.CaptureFixture[str]):
        """Уровень warning окрашивает сообщение в жёлтый."""
        logger = ConsoleLogger(use_colors=True)
        scope = LogScope(action="MyAction")
        ctx = make_context()
        params = ParamsTest()

        await logger.write(scope, "Warning message", {"level": "warning"}, ctx, {}, params, 0)

        captured = capsys.readouterr()
        assert "\033[33mWarning message\033[0m" in captured.out

    @pytest.mark.anyio
    async def test_write_error_level_red(self, capsys: pytest.CaptureFixture[str]):
        """Уровень error окрашивает сообщение в красный."""
        logger = ConsoleLogger(use_colors=True)
        scope = LogScope(action="MyAction")
        ctx = make_context()
        params = ParamsTest()

        await logger.write(scope, "Error message", {"level": "error"}, ctx, {}, params, 0)

        captured = capsys.readouterr()
        assert "\033[31mError message\033[0m" in captured.out

    @pytest.mark.anyio
    async def test_write_debug_level_grey(self, capsys: pytest.CaptureFixture[str]):
        """Уровень debug окрашивает сообщение в серый."""
        logger = ConsoleLogger(use_colors=True)
        scope = LogScope(action="MyAction")
        ctx = make_context()
        params = ParamsTest()

        await logger.write(scope, "Debug message", {"level": "debug"}, ctx, {}, params, 0)

        captured = capsys.readouterr()
        assert "\033[90mDebug message\033[0m" in captured.out

    @pytest.mark.anyio
    async def test_write_unknown_level_no_color(self, capsys: pytest.CaptureFixture[str]):
        """Неизвестный уровень не добавляет цвета сообщению (но скоуп остаётся серым)."""
        logger = ConsoleLogger(use_colors=True)
        scope = LogScope(action="MyAction")
        ctx = make_context()
        params = ParamsTest()

        await logger.write(scope, "Plain message", {"level": "custom"}, ctx, {}, params, 0)

        captured = capsys.readouterr()
        # Сообщение без ANSI-кодов цвета (проверяем отсутствие зелёного, жёлтого, красного, серого для сообщения)
        assert "\033[32m" not in captured.out  # нет зелёного
        assert "\033[33m" not in captured.out  # нет жёлтого
        assert "\033[31m" not in captured.out  # нет красного
        # Серый цвет допустим только для скоупа, но не для сообщения.
        # Проверим, что сам текст "Plain message" не обёрнут в серый.
        # Проще: проверить, что в строке нет подстроки "\033[90mPlain message".
        # Но лучше извлечь часть после скоупа и проверить отсутствие ANSI-кодов.
        # Воспользуемся тем, что сообщение выводится после скоупа и квадратной скобки.
        # Можно проверить, что после закрывающей скобки нет ANSI-кодов.
        # Упростим: проверим, что "\033[90m" не встречается дважды (один раз для скоупа допустим).
        # Но точнее: после скоупа идёт пробел, затем сообщение. Если сообщение не окрашено, то после пробела нет \033.
        # Проверим, что в строке ровно одно вхождение \033[90m (для скоупа).
        assert captured.out.count("\033[90m") == 1
        # Проверим, что нет других цветов.
        assert "\033[32m" not in captured.out
        assert "\033[33m" not in captured.out
        assert "\033[31m" not in captured.out

    @pytest.mark.anyio
    async def test_write_level_with_none_marker(self, capsys: pytest.CaptureFixture[str]):
        """Одновременная раскраска уровня и маркера <none> работает корректно."""
        logger = ConsoleLogger(use_colors=True)
        scope = LogScope(action="MyAction")
        ctx = make_context()
        params = ParamsTest()

        await logger.write(scope, "user=<none>", {"level": "error"}, ctx, {}, params, 0)

        captured = capsys.readouterr()
        # Сообщение красное (error), <none> тоже красное (но это не видно, т.к. уже красное)
        # Проверим, что оба кода присутствуют
        assert "\033[31muser=<none>\033[0m" in captured.out or \
               ("\033[31muser=" in captured.out and "\033[31m<none>\033[0m" in captured.out)

    # ------------------------------------------------------------------
    # ТЕСТЫ: Отсутствие уровня
    # ------------------------------------------------------------------

    @pytest.mark.anyio
    async def test_write_without_level_defaults_to_info(self, capsys: pytest.CaptureFixture[str]):
        """Если level отсутствует в var, по умолчанию используется info (зелёный)."""
        logger = ConsoleLogger(use_colors=True)
        scope = LogScope(action="MyAction")
        ctx = make_context()
        params = ParamsTest()

        # Не передаём level
        await logger.write(scope, "Default message", {}, ctx, {}, params, 0)

        captured = capsys.readouterr()
        assert "\033[32mDefault message\033[0m" in captured.out

    # ------------------------------------------------------------------
    # ТЕСТЫ: Множественные вызовы
    # ------------------------------------------------------------------

    @pytest.mark.anyio
    async def test_multiple_writes(self, capsys: pytest.CaptureFixture[str]):
        """Несколько вызовов write выводят несколько строк с правильными цветами."""
        logger = ConsoleLogger(use_colors=True)
        scope = LogScope(action="Test")
        ctx = make_context()
        params = ParamsTest()

        await logger.write(scope, "first", {"level": "info"}, ctx, {}, params, 0)
        await logger.write(scope, "second", {"level": "warning"}, ctx, {}, params, 1)
        await logger.write(scope, "third", {"level": "error"}, ctx, {}, params, 2)

        captured = capsys.readouterr()
        lines = captured.out.strip().split("\n")
        assert len(lines) == 3
        # Первая строка: зелёное "first"
        assert "\033[32mfirst\033[0m" in lines[0]
        # Вторая строка: жёлтое "second" с отступом
        assert "  " in lines[1]
        assert "\033[33msecond\033[0m" in lines[1]
        # Третья строка: красное "third" с двойным отступом
        assert "    " in lines[2]
        assert "\033[31mthird\033[0m" in lines[2]