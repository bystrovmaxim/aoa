"""
Консольный логер для системы логирования AOA.
Реализует вывод сообщений в консоль через print с поддержкой
отступов по уровню indent и опциональной ANSI-раскраски.

Поддерживает уровни логирования (info, warning, error, debug),
которые передаются в var["level"] и определяют цвет сообщения:
- info: зелёный
- warning: жёлтый
- error: красный
- debug: серый

Если уровень не указан, используется "info".
"""

from typing import Any

from action_machine.Context.context import Context
from action_machine.Core.BaseParams import BaseParams
from action_machine.Core.BaseState import BaseState
from action_machine.Logging.base_logger import BaseLogger
from action_machine.Logging.log_scope import LogScope

# ANSI escape-коды для раскраски элементов вывода.
_ANSI_GREY = "\033[90m"    # Серый — для скоупа (служебная информация)
_ANSI_GREEN = "\033[32m"   # Зелёный — для info
_ANSI_YELLOW = "\033[33m"  # Жёлтый — для warning
_ANSI_RED = "\033[31m"     # Красный — для error и маркера <none>
_ANSI_RESET = "\033[0m"    # Сброс цвета

# Маркер неразрешённой переменной, подставляемый координатором
# при невозможности найти значение по dot-path.
_NONE_MARKER = "<none>"


class ConsoleLogger(BaseLogger):
    """
    Логер, выводящий сообщения в консоль через print.
    Поддерживает ANSI-раскраску и отступы по уровню indent.
    Наследует фильтрацию из BaseLogger — метод write вызывается
    только если сообщение прошло все фильтры.

    Цвет сообщения зависит от уровня логирования (var["level"]):
        info    → зелёный
        warning → жёлтый
        error   → красный
        debug   → серый

    Атрибуты:
        _use_colors: включена ли ANSI-раскраска вывода.
    """

    def __init__(
        self,
        filters: list[str] | None = None,
        use_colors: bool = True,
    ) -> None:
        """
        Создаёт консольный логер.

        Аргументы:
            filters: список строк-регулярных выражений для фильтрации.
                     None или пустой список означает «принимать всё».
            use_colors: если True — вывод раскрашивается ANSI-кодами.
                        Если False — чистый текст без escape-последовательностей.
                        По умолчанию True.
        """
        super().__init__(filters=filters)
        self._use_colors: bool = use_colors

    def _colorize_scope(self, scope_text: str) -> str:
        """
        Раскрашивает текст скоупа серым цветом.

        Аргументы:
            scope_text: строка скоупа из scope.as_dotpath().

        Возвращает:
            Раскрашенная строка если use_colors=True,
            иначе исходная строка без изменений.
        """
        if self._use_colors and scope_text:
            return f"{_ANSI_GREY}{scope_text}{_ANSI_RESET}"
        return scope_text

    def _colorize_by_level(self, message: str, level: str) -> str:
        """
        Раскрашивает сообщение в соответствии с уровнем логирования.

        Аргументы:
            message: текст сообщения (после подстановок).
            level: уровень логирования ("info", "warning", "error", "debug").

        Возвращает:
            Строка с ANSI-кодами если use_colors=True и уровень известен,
            иначе исходная строка без изменений.
        """
        if not self._use_colors:
            return message

        if level == "info":
            color = _ANSI_GREEN
        elif level == "warning":
            color = _ANSI_YELLOW
        elif level == "error":
            color = _ANSI_RED
        elif level == "debug":
            color = _ANSI_GREY
        else:
            # Неизвестный уровень — без цвета
            return message

        return f"{color}{message}{_ANSI_RESET}"

    def _colorize_message(self, message: str, level: str) -> str:
        """
        Полная раскраска сообщения: сначала по уровню, затем замена <none> красным.
        Если use_colors=False, возвращает исходное сообщение.

        Аргументы:
            message: текст сообщения с уже выполненными подстановками.
            level: уровень логирования.

        Возвращает:
            Строка с ANSI-кодами для цвета уровня и красного <none>.
        """
        if not self._use_colors:
            return message

        # Сначала цвет уровня
        colored = self._colorize_by_level(message, level)
        # Затем красный <none> поверх (заменяем все вхождения)
        colored = colored.replace(_NONE_MARKER, f"{_ANSI_RED}{_NONE_MARKER}{_ANSI_RESET}")
        return colored

    def _format_line(
        self,
        scope: LogScope,
        message: str,
        indent: int,
    ) -> str:
        """
        Собирает финальную строку для вывода в консоль.
        Формат: {indent_str}[{scope_dotpath}] {message}
        Если скоуп пуст — квадратные скобки не выводятся.

        Аргументы:
            scope: скоуп текущего вызова логера.
            message: текст сообщения с подстановками (уже раскрашенный).
            indent: уровень отступа (каждый уровень = 2 пробела).

        Возвращает:
            Готовая строка для print.
        """
        indent_str = "  " * indent
        dotpath = scope.as_dotpath()
        if dotpath:
            scope_part = self._colorize_scope(dotpath)
            return f"{indent_str}[{scope_part}] {message}"
        return f"{indent_str}{message}"

    async def write(  # pylint: disable=too-many-positional-arguments
        self,
        scope: LogScope,
        message: str,
        var: dict[str, Any],
        ctx: Context,
        state: BaseState,
        params: BaseParams,
        indent: int,
    ) -> None:
        """
        Выводит сообщение в консоль через print.
        Вызывается из BaseLogger.handle только после успешной фильтрации.

        Определяет уровень логирования из var.get("level", "info").
        Раскрашивает сообщение в соответствии с уровнем и подставляет
        красный цвет для маркера <none> (если use_colors=True).

        Никакого try/except — если print упал, исключение летит наверх.

        Аргументы:
            scope: скоуп текущего вызова (местоположение в конвейере).
            message: текст сообщения с подставленными переменными.
            var: словарь переменных, переданных разработчиком в log.
            ctx: контекст выполнения (пользователь, запрос, окружение).
            state: текущее состояние конвейера.
            params: входные параметры действия.
            indent: уровень отступа (для вложенных вызовов).
        """
        level = var.get("level", "info")
        colored_message = self._colorize_message(message, level)
        line = self._format_line(scope, colored_message, indent)
        print(line)