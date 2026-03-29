# src/action_machine/logging/log_scope.py
"""
Scope логирования — хранит информацию о местоположении в конвейере выполнения.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

LogScope — объект, описывающий контекст вызова логгера: в каком действии,
аспекте, плагине, на каком уровне вложенности и при каком событии
происходит логирование. Значения передаются как kwargs и становятся
атрибутами экземпляра.

Наследует ReadableMixin, поэтому поддерживает dict-подобный доступ:
    scope['action'], scope.get('aspect'), 'nest_level' in scope

═══════════════════════════════════════════════════════════════════════════════
ПОЛЯ SCOPE ДЛЯ АСПЕКТОВ
═══════════════════════════════════════════════════════════════════════════════

При логировании из аспектов действий (через ToolsBox.info/warning/error/debug)
ScopedLogger создаёт LogScope со следующими полями:

    machine    : str — имя класса машины ("ActionProductMachine").
    mode       : str — режим выполнения ("production", "test", "staging").
    action     : str — полное имя класса действия (модуль + класс).
    aspect     : str — имя метода-аспекта ("validate_amount", "process_payment").
    nest_level : int — уровень вложенности вызова (0 для корневого, 1 для
                       дочернего через box.run(), 2 для вложенного в дочернее и т.д.).

═══════════════════════════════════════════════════════════════════════════════
ПОЛЯ SCOPE ДЛЯ ПЛАГИНОВ
═══════════════════════════════════════════════════════════════════════════════

При логировании из обработчиков плагинов (через параметр log в @on-методах)
создаётся LogScope со следующими полями:

    machine    : str — имя класса машины.
    mode       : str — режим выполнения.
    plugin     : str — имя класса плагина ("MetricsPlugin", "AuditPlugin").
    action     : str — полное имя действия, для которого сработало событие.
    event      : str — имя события ("global_start", "global_finish",
                       "before:validate", "after:process_payment").
    nest_level : int — уровень вложенности вызова.

═══════════════════════════════════════════════════════════════════════════════
ИСПОЛЬЗОВАНИЕ В ШАБЛОНАХ
═══════════════════════════════════════════════════════════════════════════════

Все поля scope доступны в шаблонах логирования через namespace {%scope.*}:

    "{%scope.action}"       → "module.CreateOrderAction"
    "{%scope.aspect}"       → "process_payment"
    "{%scope.nest_level}"   → "0"
    "{%scope.plugin}"       → "MetricsPlugin"
    "{%scope.event}"        → "global_finish"
    "{%scope.machine}"      → "ActionProductMachine"
    "{%scope.mode}"         → "production"

═══════════════════════════════════════════════════════════════════════════════
МЕТОД as_dotpath()
═══════════════════════════════════════════════════════════════════════════════

Возвращает все непустые значения, объединённые точками, в порядке передачи
kwargs. Используется при формировании строки для фильтрации в BaseLogger.

Пример для аспекта:
    LogScope(machine="APM", mode="prod", action="OrderAction", aspect="validate")
    → "APM.prod.OrderAction.validate"

Пример для плагина:
    LogScope(machine="APM", mode="prod", plugin="Metrics", action="OrderAction", event="global_finish")
    → "APM.prod.Metrics.OrderAction.global_finish"

Результат кешируется после первого вызова.

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР СОЗДАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    # Scope для аспекта действия
    scope = LogScope(
        machine="ActionProductMachine",
        mode="production",
        action="module.CreateOrderAction",
        aspect="process_payment",
        nest_level=0,
    )

    # Scope для обработчика плагина
    scope = LogScope(
        machine="ActionProductMachine",
        mode="production",
        plugin="MetricsPlugin",
        action="module.CreateOrderAction",
        event="global_finish",
        nest_level=1,
    )
"""

from typing import Any

from action_machine.core.readable_mixin import ReadableMixin


class LogScope(ReadableMixin):
    """
    Scope логирования — хранит информацию о местоположении в конвейере.

    Значения передаются как kwargs и становятся атрибутами экземпляра.
    Наследует ReadableMixin, поддерживая dict-подобный доступ:
    scope['action'], scope.get('aspect'), scope.keys() и т.д.

    Поддерживаемые поля (все опциональные, задаются через kwargs):
        machine    : str — имя класса машины.
        mode       : str — режим выполнения.
        action     : str — полное имя класса действия.
        aspect     : str — имя метода-аспекта (для scope аспектов).
        plugin     : str — имя класса плагина (для scope плагинов).
        event      : str — имя события (для scope плагинов).
        nest_level : int — уровень вложенности вызова действия.

    Атрибуты:
        _key_order : list[str]
            Порядок ключей для формирования dotpath. Сохраняется
            при создании, определяет результат as_dotpath().
        _cached_path : str | None
            Кешированный результат as_dotpath(). Вычисляется один раз
            при первом вызове.
    """

    def __init__(self, **kwargs: Any) -> None:
        """
        Инициализирует scope с произвольным набором именованных аргументов.

        Каждый kwarg становится атрибутом экземпляра. Порядок kwargs
        сохраняется для формирования dotpath.

        Аргументы:
            **kwargs: произвольные именованные аргументы, задающие поля scope.
                      Типичные ключи: machine, mode, action, aspect, plugin,
                      event, nest_level.
        """
        for key, value in kwargs.items():
            setattr(self, key, value)
        self._key_order = list(kwargs.keys())
        self._cached_path: str | None = None

    def as_dotpath(self) -> str:
        """
        Возвращает все непустые строковые значения, объединённые точками.

        Порядок определяется порядком kwargs при создании.
        Числовые значения (например, nest_level) преобразуются в строку.
        Пустые строки и None пропускаются.
        Результат кешируется после первого вызова.

        Возвращает:
            str — dotpath вида "machine.mode.action.aspect" или пустая строка.

        Пример:
            >>> scope = LogScope(machine="APM", mode="prod", action="Order", aspect="validate")
            >>> scope.as_dotpath()
            'APM.prod.Order.validate'
        """
        if self._cached_path is None:
            values = []
            for key in self._key_order:
                val = getattr(self, key, None)
                if val is not None and val != "":
                    values.append(str(val))
            self._cached_path = ".".join(values)
        return self._cached_path

    def to_dict(self) -> dict[str, Any]:
        """
        Возвращает словарь со всеми полями scope в порядке создания.

        Используется для отладки, сериализации и передачи в шаблоны.

        Возвращает:
            dict[str, Any] — словарь {ключ: значение} для всех полей scope.
        """
        return {key: getattr(self, key) for key in self._key_order}
