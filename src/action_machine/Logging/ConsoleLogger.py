# ActionMachine/Logging/ConsoleLogger.py
"""
Консольный логер для системы логирования AOA.

Реализует вывод сообщений в консоль через print с поддержкой
отступов по уровню indent и опциональной ANSI-раскраски.

Раскраска привязана к семантике элементов сообщения:
- Скоуп (dotpath) выводится серым цветом — это служебная информация
  о местоположении в конвейере, не перетягивающая внимание.
- Пользовательское сообщение выводится белым (дефолтным) цветом —
  это основная информация, которую пишет разработчик.
- Подстановки переменных, которые были успешно разрешены,
  выводятся зелёным — они несут динамические данные.
- Маркер <none> для неразрешённых переменных выводится красным —
  это сигнал что что-то не найдено и требует внимания.

При use_colors=False весь вывод идёт без ANSI-кодов.
Это полезно для записи в файл, CI-окружений и любых ситуаций
где терминал не поддерживает escape-последовательности.

ConsoleLogger наследует BaseLogger и реализует единственный
абстрактный метод write. Фильтрация выполняется в BaseLogger.handle
до вызова write — если сообщение дошло до write, оно уже прошло
все фильтры.

Никакого подавления исключений. Если print упал (например,
перенаправление в закрытый pipe) — исключение летит наверх.
Логер должен падать громко [1].

Пример создания и использования:

    Без фильтров, с цветами (по умолчанию):
    >>> logger = ConsoleLogger()

    С фильтрами, без цветов:
    >>> logger = ConsoleLogger(
    ...     filters=[r"ProcessOrder.*"],
    ...     use_colors=False
    ... )

    Вывод с отступом indent=2:
    >>> await logger.write(scope, "Загружено 150 задач", {}, ctx, {}, params, indent=2)
    # Выведет:  "    [ProcessOrder.validate] Загружено 150 задач"
    #           (4 пробела отступа = 2 * "  ")

Формат строки вывода:
    {indent}[{scope_dotpath}] {message}

    Где:
    - indent — отступ из пробелов, "  " * indent (два пробела на уровень).
    - scope_dotpath — результат scope.as_dotpath(), серый при use_colors=True.
    - message — текст сообщения с выполненными подстановками.
"""

from typing import Any

from action_machine.Context.Context import Context
from action_machine.Core.BaseParams import BaseParams
from action_machine.Logging.BaseLogger import base_logger
from action_machine.Logging.LogScope import log_scope

# ANSI escape-коды для раскраски элементов вывода.
# Каждый код привязан к семантической роли элемента,
# а не к «уровню логирования» (уровней пока нет).
_ANSI_GREY = "\033[90m"
_ANSI_GREEN = "\033[32m"
_ANSI_RED = "\033[31m"
_ANSI_RESET = "\033[0m"

# Маркер неразрешённой переменной, подставляемый координатором
# при невозможности найти значение по dot-path.
_NONE_MARKER = "<none>"


class console_logger(base_logger):
    """
    Логер, выводящий сообщения в консоль через print.

    Поддерживает ANSI-раскраску и отступы по уровню indent.
    Наследует фильтрацию из BaseLogger — метод write вызывается
    только если сообщение прошло все фильтры.

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
                     Каждая строка компилируется в re.Pattern в BaseLogger.
                     None или пустой список означает «принимать всё».
            use_colors: если True — вывод раскрашивается ANSI-кодами.
                        Если False — чистый текст без escape-последовательностей.
                        По умолчанию True.

        Пример:
            >>> logger = ConsoleLogger(filters=[r"Payment.*"], use_colors=True)
            >>> logger = ConsoleLogger(use_colors=False)  # для CI/файлов
        """
        super().__init__(filters=filters)
        self._use_colors: bool = use_colors

    def _colorize_scope(self, scope_text: str) -> str:
        """
        Раскрашивает текст скоупа серым цветом.

        Скоуп — это служебная информация о местоположении
        в конвейере (action, aspect, event). Серый цвет
        не перетягивает внимание с основного сообщения.

        Аргументы:
            scope_text: строка скоупа из scope.as_dotpath().

        Возвращает:
            Раскрашенная строка если use_colors=True,
            иначе исходная строка без изменений.

        Пример:
            >>> logger._colorize_scope("ProcessOrder.validate")
            '\\033[90mProcessOrder.validate\\033[0m'
        """
        if self._use_colors and scope_text:
            return f"{_ANSI_GREY}{scope_text}{_ANSI_RESET}"
        return scope_text

    def _colorize_message(self, message: str) -> str:
        """
        Раскрашивает элементы внутри сообщения по семантике.

        Обрабатывает два типа элементов:
        1. Маркер <none> — раскрашивается красным. Это сигнал
           что переменная не была разрешена при подстановке.
        2. Остальной текст — остаётся без изменений (дефолтный цвет).

        Аргументы:
            message: текст сообщения с уже выполненными подстановками.

        Возвращает:
            Строка с ANSI-кодами вокруг <none> если use_colors=True,
            иначе исходная строка без изменений.

        Пример:
            >>> logger._colorize_message("user=42 role=<none>")
            'user=42 role=\\033[31m<none>\\033[0m'
        """
        if not self._use_colors:
            return message

        # Раскрашиваем каждое вхождение <none> красным.
        # Остальной текст остаётся дефолтным.
        return message.replace(_NONE_MARKER, f"{_ANSI_RED}{_NONE_MARKER}{_ANSI_RESET}")

    def _format_line(
        self,
        scope: log_scope,
        message: str,
        indent: int,
    ) -> str:
        """
        Собирает финальную строку для вывода в консоль.

        Формат: {indent_str}[{scope_dotpath}] {message}

        Если скоуп пуст (пустой dotpath) — квадратные скобки
        не выводятся, только отступ и сообщение.

        Аргументы:
            scope: скоуп текущего вызова логера.
            message: текст сообщения с подстановками.
            indent: уровень отступа (количество уровней,
                    каждый уровень = 2 пробела).

        Возвращает:
            Готовая строка для print.

        Пример:
            >>> logger._format_line(scope, "OK", indent=1)
            '  [ProcessOrder.validate] OK'
        """
        indent_str = "  " * indent
        dotpath = scope.as_dotpath()

        if dotpath:
            scope_part = self._colorize_scope(dotpath)
            colored_message = self._colorize_message(message)
            return f"{indent_str}[{scope_part}] {colored_message}"
        else:
            colored_message = self._colorize_message(message)
            return f"{indent_str}{colored_message}"

    async def write(
        self,
        scope: log_scope,
        message: str,
        var: dict[str, Any],
        context: Context,
        state: dict[str, Any],
        params: BaseParams,
        indent: int,
    ) -> None:
        """
        Выводит сообщение в консоль через print.

        Вызывается из BaseLogger.handle только после успешной
        фильтрации через match_filters. Если сообщение дошло
        до этого метода — оно уже прошло все фильтры.

        Формирует строку с учётом отступа indent и скоупа,
        применяет ANSI-раскраску если use_colors=True,
        и вызывает print.

        Никакого try/except. Если print упал — исключение
        летит наверх. Логер должен падать громко.

        Аргументы:
            scope: скоуп текущего вызова (местоположение в конвейере).
            message: текст сообщения с подставленными переменными.
            var: словарь переменных, переданных разработчиком в log.
            context: контекст выполнения (пользователь, запрос, окружение).
            state: текущее состояние конвейера.
            params: входные параметры действия.
            indent: уровень отступа (для вложенных вызовов).

        Пример вывода (use_colors=True, indent=1):
            [ProcessOrder.validate] Загружено 150 задач amount=1500.0
            (с серым скоупом и красными <none> если есть)

        Пример вывода (use_colors=False, indent=0):
            [ProcessOrder.validate] Загружено 150 задач amount=1500.0
        """
        line = self._format_line(scope, message, indent)
        print(line)
