# ActionMachine/Logging/BaseLogger.py
"""
Абстрактный базовый класс для всех логеров системы логирования AOA.

BaseLogger определяет двухфазный протокол обработки сообщений:
1. Фильтрация — метод match_filters быстро определяет,
   нужно ли обрабатывать сообщение данным логером.
2. Запись — абстрактный метод write реализуется в наследниках
   и выполняет конкретную работу (вывод в консоль, запись в файл,
   отправка в ELK и т.д.).

Фильтрация основана на регулярных выражениях. Каждый логер получает
список фильтров при создании. Фильтры компилируются в __init__
для производительности (не компилируются при каждом вызове).
Строка для проверки собирается из scope.as_dotpath() и сериализованных
ключей var — это позволяет фильтровать по любому сочетанию условий.

Если список фильтров пуст — логер пропускает все сообщения (нет фильтров
означает «принимать всё»). Если хотя бы один фильтр дал match — сообщение
принимается. Если ни один не совпал — сообщение отбрасывается.

BaseLogger НЕ подавляет исключения. Если метод write упал — исключение
летит наверх по стеку. Это сознательное решение: сломанный логер
должен быть обнаружен немедленно, а не через месяц когда понадобятся
логи которых нет [1].

Все методы асинхронные — логер может выполнять IO-операции
(запись в файл, отправка по сети) без блокировки event loop.

Пример создания конкретного логера:

    >>> class MyLogger(BaseLogger):
    ...     async def write(self, scope, message, var, context, state, params, indent):
    ...         print(message)
    ...
    >>> logger = MyLogger(filters=[r"ProcessOrder.*"])

Пример с пустыми фильтрами (принимает всё):

    >>> logger = MyLogger(filters=[])
"""

import re
from abc import ABC, abstractmethod
from typing import Any

from action_machine.Context.context import Context
from action_machine.Core.BaseParams import BaseParams
from action_machine.Logging.log_scope import LogScope


class BaseLogger(ABC):
    """
    Абстрактный базовый класс для всех логеров.

    Определяет протокол обработки сообщений: фильтрация через
    регулярные выражения, затем запись через абстрактный метод write.

    Наследники реализуют только метод write — фильтрация и вызов
    write обеспечиваются базовым классом через метод handle.

    Исключения из write не подавляются — если логер сломан,
    система должна узнать об этом немедленно.
    """

    def __init__(self, filters: list[str] | None = None) -> None:
        """
        Инициализирует логер с набором фильтров.

        Фильтры — это строки регулярных выражений, которые компилируются
        при создании экземпляра для повышения производительности.
        Каждый фильтр применяется через re.search (не fullmatch),
        что позволяет искать совпадение в любом месте строки контекста.

        Если filters пуст или None — фильтрация отключена,
        логер принимает все сообщения.

        Аргументы:
            filters: список строк-регулярных выражений для фильтрации.
                     Каждая строка компилируется в re.Pattern.
                     None или пустой список означает «принимать всё».

        Пример:
            >>> logger = MyLogger(filters=[r"ProcessOrder.*", r"Payment"])
            >>> logger = MyLogger(filters=[])  # принимает всё
            >>> logger = MyLogger()            # принимает всё
        """
        self._filters: list[re.Pattern[str]] = [re.compile(f) for f in (filters or [])]

    def _build_filter_string(
        self,
        scope: LogScope,
        message: str,
        var: dict[str, Any],
    ) -> str:
        """
        Собирает строку контекста для проверки фильтрами.

        Строка формируется из трёх частей:
        1. scope.as_dotpath() — местоположение в конвейере
           (например, "ProcessOrderAction.validate_user.before").
        2. Текст сообщения message.
        3. Сериализованные ключи и значения var в формате "key=value".

        Части разделяются пробелом. Это позволяет фильтровать
        по любому сочетанию: по имени action, по тексту сообщения,
        по значениям переменных.

        Аргументы:
            scope: скоуп текущего вызова логера.
            message: текст сообщения (уже с подставленными переменными).
            var: словарь переменных, переданных в log.

        Возвращает:
            Строка контекста для применения регулярных выражений.

        Пример:
            >>> scope = LogScope(action="ProcessOrder", aspect="validate")
            >>> result = logger._build_filter_string(scope, "OK", {"amount": 100})
            >>> # "ProcessOrder.validate OK amount=100"
        """
        parts: list[str] = []

        # Часть 1: dotpath скоупа
        dotpath = scope.as_dotpath()
        if dotpath:
            parts.append(dotpath)

        # Часть 2: текст сообщения
        if message:
            parts.append(message)

        # Часть 3: сериализованные переменные var
        for key, value in var.items():
            parts.append(f"{key}={value}")

        return " ".join(parts)

    async def match_filters(
        self,
        scope: LogScope,
        message: str,
        var: dict[str, Any],
        ctx: Context,
        state: dict[str, Any],
        params: BaseParams,
        indent: int,
    ) -> bool:
        """
        Проверяет, должен ли данный логер обработать сообщение.

        Логика фильтрации:
        1. Если список фильтров пуст — возвращает True (нет фильтров,
           принимаем всё).
        2. Собирает строку контекста через _build_filter_string.
        3. Применяет каждый скомпилированный re.Pattern через search.
        4. Как только один фильтр дал совпадение — возвращает True.
        5. Если ни один фильтр не совпал — возвращает False.

        Метод асинхронный для единообразия интерфейса, хотя текущая
        реализация не выполняет IO-операций.

        Аргументы:
            scope: скоуп текущего вызова (местоположение в конвейере).
            message: текст сообщения с подставленными переменными.
            var: словарь переменных, переданных разработчиком в log.
            context: контекст выполнения (пользователь, запрос, окружение).
            state: текущее состояние конвейера.
            params: входные параметры действия.
            indent: уровень отступа (для вложенных вызовов).

        Возвращает:
            True если сообщение прошло фильтрацию и должно быть записано.
            False если сообщение отклонено всеми фильтрами.

        Пример:
            >>> logger = MyLogger(filters=[r"ProcessOrder"])
            >>> scope = LogScope(action="ProcessOrderAction")
            >>> await logger.match_filters(scope, "OK", {}, ctx, {}, params, 0)
            True
            >>> scope2 = LogScope(action="DeleteUserAction")
            >>> await logger.match_filters(scope2, "OK", {}, ctx, {}, params, 0)
            False
        """
        # Нет фильтров — принимаем всё
        if not self._filters:
            return True

        # Собираем строку контекста
        filter_string = self._build_filter_string(scope, message, var)

        # Проверяем каждый фильтр — первое совпадение достаточно
        for pattern in self._filters:
            if pattern.search(filter_string):
                return True

        # Ни один фильтр не совпал
        return False

    async def handle(
        self,
        scope: LogScope,
        message: str,
        var: dict[str, Any],
        ctx: Context,
        state: dict[str, Any],
        params: BaseParams,
        indent: int,
    ) -> None:
        """
        Точка входа для обработки сообщения логером.

        Вызывается координатором LogCoordinator в цикле для каждого
        зарегистрированного логера. Выполняет две фазы:

        1. Фильтрация — вызывает match_filters. Если False — выходит
           без дальнейших действий (сообщение не интересно этому логеру).
        2. Запись — вызывает абстрактный метод write, который реализуется
           в конкретных наследниках.

        Никакого try/except. Если write упал — исключение летит наверх.
        Логер должен падать громко. Если логер сломан, разработчик
        узнает об этом немедленно, а не через месяц когда нужны логи
        которых нет.

        Аргументы:
            scope: скоуп текущего вызова (местоположение в конвейере).
            message: текст сообщения с подставленными переменными.
            var: словарь переменных, переданных разработчиком в log.
            context: контекст выполнения (пользователь, запрос, окружение).
            state: текущее состояние конвейера.
            params: входные параметры действия.
            indent: уровень отступа (для вложенных вызовов).

        Пример:
            >>> await logger.handle(scope, "Загружено 150 задач", {"count": 150},
            ...                     context, state, params, indent=2)
        """
        # Фаза 1: фильтрация
        matched = await self.match_filters(scope, message, var, ctx, state, params, indent)
        if not matched:
            return

        # Фаза 2: запись (абстрактный метод)
        await self.write(scope, message, var, ctx, state, params, indent)

    @abstractmethod
    async def write(
        self,
        scope: LogScope,
        message: str,
        var: dict[str, Any],
        ctx: Context,
        state: dict[str, Any],
        params: BaseParams,
        indent: int,
    ) -> None:
        """
        Записывает сообщение в конкретный канал вывода.

        Абстрактный метод — реализуется в каждом конкретном логере.
        ConsoleLogger выводит в консоль через print,
        FileLogger пишет в файл, ElkLogger отправляет в ELK и т.д.

        Метод вызывается только если match_filters вернул True —
        фильтрация уже пройдена на этапе handle.

        Метод НЕ должен подавлять исключения. Если запись не удалась —
        исключение должно пройти наверх без перехвата.

        Аргументы:
            scope: скоуп текущего вызова (местоположение в конвейере).
            message: текст сообщения с подставленными переменными.
            var: словарь переменных, переданных разработчиком в log.
            context: контекст выполнения (пользователь, запрос, окружение).
            state: текущее состояние конвейера.
            params: входные параметры действия.
            indent: уровень отступа (для вложенных вызовов).

        Пример реализации в наследнике:
            >>> async def write(self, scope, message, var, context, state, params, indent):
            ...     prefix = "  " * indent
            ...     print(f"{prefix}[{scope.as_dotpath()}] {message}")
        """
        pass
