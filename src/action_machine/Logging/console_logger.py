# src/action_machine/logging/console_logger.py
"""
Консольный логгер для системы логирования ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

ConsoleLogger выводит сообщения в stdout через print. Поддерживает:

- Отступы на основе уровня вложенности (nest_level), передаваемого
  в параметре indent при вызове write().
- Включение/отключение отступов через параметр use_indent.
- Настройку ширины одного уровня отступа через indent_size.
- Сохранение или удаление ANSI-цветов через use_colors.

Цвета применяются через шаблонные фильтры (например, {%var.amount|red})
и обрабатываются координатором логирования (LogCoordinator). ConsoleLogger
сам не добавляет никаких автоматических цветов — он только решает,
сохранять или удалять ANSI-коды, уже присутствующие в сообщении.

ANSI-коды удаляются на двух уровнях:
- LogCoordinator проверяет logger.supports_colors и вызывает strip перед
  передачей в handle().
- ConsoleLogger.write() дополнительно удаляет ANSI-коды если use_colors=False,
  чтобы гарантировать чистый вывод даже при прямом вызове write() без
  координатора (например, в тестах или при кастомной интеграции).

═══════════════════════════════════════════════════════════════════════════════
ПАРАМЕТРЫ КОНСТРУКТОРА
═══════════════════════════════════════════════════════════════════════════════

    filters : list[str] | None
        Список регулярных выражений для фильтрации сообщений.
        None или пустой список — принимать всё. Наследуется от BaseLogger.

    use_colors : bool (по умолчанию True)
        Если True — ANSI-коды сохраняются в выводе. Полезно для терминалов
        с поддержкой цветов (локальная разработка, iTerm2, VS Code Terminal).
        Если False — ANSI-коды удаляются перед выводом. Полезно для
        production-логов, отправляемых в ELK/Loki.

    use_indent : bool (по умолчанию True)
        Если True — сообщения сдвигаются вправо на indent * indent_size
        пробелов, где indent — уровень вложенности (nest_level), переданный
        машиной. Визуально показывает иерархию вложенных действий.
        Если False — все сообщения выводятся без отступов. Полезно для
        production-логов, где отступы мешают парсингу.

    indent_size : int (по умолчанию 2)
        Количество пробелов на один уровень вложенности.
        Используется только при use_indent=True. По умолчанию 2.
        Для более наглядной иерархии можно установить 4.

═══════════════════════════════════════════════════════════════════════════════
ФОРМАТ ВЫВОДА
═══════════════════════════════════════════════════════════════════════════════

С отступами (use_indent=True, indent_size=2):

    [INFO] Начало обработки заказа
      [INFO] Валидация карты                    ← nest_level=1
      [INFO] Списание средств                   ← nest_level=1
        [INFO] Проверка лимита                  ← nest_level=2
    [INFO] Заказ обработан

Без отступов (use_indent=False):

    [INFO] Начало обработки заказа
    [INFO] Валидация карты
    [INFO] Списание средств
    [INFO] Проверка лимита
    [INFO] Заказ обработан

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    # Для локальной разработки — цвета и отступы
    logger = ConsoleLogger()

    # Для CI/CD — без цветов, с отступами
    logger = ConsoleLogger(use_colors=False)

    # Для production (ELK/Loki) — без цветов, без отступов
    logger = ConsoleLogger(use_colors=False, use_indent=False)

    # Для отладки — широкие отступы
    logger = ConsoleLogger(use_indent=True, indent_size=4)

    # С фильтрами — только определённые действия
    logger = ConsoleLogger(filters=[r"CreateOrder", r"ProcessPayment"])

    # Передача в координатор логирования
    log_coordinator = LogCoordinator(loggers=[logger])

    # Передача в машину
    machine = ActionProductMachine(
        mode="production",
        log_coordinator=log_coordinator,
    )
"""

from typing import Any

from action_machine.context.context import Context
from action_machine.core.base_params import BaseParams
from action_machine.core.base_state import BaseState
from action_machine.logging.base_logger import BaseLogger
from action_machine.logging.log_scope import LogScope


class ConsoleLogger(BaseLogger):
    """
    Логгер, выводящий сообщения в консоль через print.

    Поддерживает настраиваемые отступы на основе уровня вложенности
    и опциональное сохранение ANSI-цветов.

    Цветизация управляется шаблонными фильтрами в координаторе;
    этот логгер не добавляет автоматических ANSI-кодов.

    При use_colors=False метод write() самостоятельно удаляет ANSI-коды
    из сообщения перед выводом, гарантируя чистый текст независимо от
    того, как был вызван write() — через координатор или напрямую.

    Атрибуты:
        _use_colors : bool
            Сохранять ли ANSI-коды в выводе. Если False, write() удаляет
            их через strip_ansi_codes() перед print.
        _use_indent : bool
            Добавлять ли отступы на основе уровня вложенности.
        _indent_size : int
            Количество пробелов на один уровень вложенности.
    """

    def __init__(
        self,
        filters: list[str] | None = None,
        use_colors: bool = True,
        use_indent: bool = True,
        indent_size: int = 2,
    ) -> None:
        """
        Создаёт консольный логгер.

        Аргументы:
            filters: список regex-паттернов для фильтрации сообщений.
                     None или пустой список — принимать всё.
            use_colors: если True — ANSI-коды сохраняются в выводе.
                        Если False — ANSI-коды удаляются перед выводом.
                        По умолчанию True.
            use_indent: если True — сообщения сдвигаются вправо
                        на indent * indent_size пробелов.
                        Если False — без отступов.
                        По умолчанию True.
            indent_size: количество пробелов на один уровень вложенности.
                         Используется только при use_indent=True.
                         По умолчанию 2.
        """
        super().__init__(filters=filters)
        self._use_colors: bool = use_colors
        self._use_indent: bool = use_indent
        self._indent_size: int = indent_size

    @property
    def supports_colors(self) -> bool:
        """
        Указывает, сохраняет ли этот логгер ANSI-коды.

        LogCoordinator проверяет это свойство перед отправкой сообщения.
        Если False — координатор удаляет ANSI-последовательности
        через BaseLogger.strip_ansi_codes() перед вызовом handle().

        Возвращает:
            True если use_colors=True, иначе False.
        """
        return self._use_colors

    def _format_line(
        self,
        message: str,
        indent: int,
    ) -> str:
        """
        Форматирует финальную строку вывода.

        Если use_indent=True — добавляет отступ из пробелов перед сообщением.
        Количество пробелов = indent * indent_size.
        Если use_indent=False — возвращает сообщение без отступов.

        Аргументы:
            message: текст сообщения (уже с подстановками и цветами).
            indent: уровень вложенности (nest_level), определяющий
                    величину отступа.

        Возвращает:
            Отформатированная строка, готовая к выводу через print.
        """
        if self._use_indent:
            indent_str = " " * (indent * self._indent_size)
            return f"{indent_str}{message}"
        return message

    async def write(
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

        Вызывается только после успешной фильтрации (match_filters
        вернул True). Не подавляет исключения — если print не удаётся,
        ошибка пробрасывается наверх.

        Если use_colors=False — удаляет ANSI-коды из сообщения перед
        выводом через strip_ansi_codes(). Это гарантирует чистый текст
        даже при прямом вызове write() без координатора.

        Аргументы:
            scope: текущий scope вызова (местоположение в конвейере).
            message: полностью подставленное сообщение (может содержать
                     ANSI-коды, если supports_colors=True).
            var: пользовательские переменные.
            ctx: контекст выполнения (пользователь, запрос, окружение).
            state: текущее состояние конвейера.
            params: входные параметры действия.
            indent: уровень вложенности (nest_level) для отступов.
        """
        if not self._use_colors:
            message = self.strip_ansi_codes(message)
        line = self._format_line(message, indent)
        print(line)
