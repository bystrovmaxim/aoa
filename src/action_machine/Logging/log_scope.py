# src/action_machine/logging/log_scope.py
"""
LogScope — scope логирования, хранит информацию о местоположении в конвейере.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

LogScope — объект, описывающий контекст вызова логгера: в каком действии,
аспекте, плагине, на каком уровне вложенности и при каком событии
происходит логирование. Значения передаются как kwargs и становятся
атрибутами экземпляра.

LogScope НЕ наследует BaseSchema. Это не pydantic-модель, а лёгкий объект
с динамическими атрибутами и dict-подобным доступом. Причина: LogScope
создаётся с произвольным набором kwargs, не имеет фиксированной схемы
полей и не нуждается в валидации типов, JSON Schema или сериализации
через model_dump(). Его единственная задача — хранить координаты
вызова и предоставлять к ним доступ через ["key"] и as_dotpath().

Навигация по полям LogScope выполняется единым DotPathNavigator
из core.navigation через duck-typed __getitem__. LogScope не наследует
BaseSchema и обрабатывается навигатором автоматически как объект
с __getitem__ интерфейсом, без явной зависимости от конкретного типа.

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
                       дочернего через box.run(), 2 для вложенного в дочернее).

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
ИСПОЛЬЗОВАНИЕ В ШАБЛОНАХ ЛОГИРОВАНИЯ
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
DICT-ПОДОБНЫЙ ДОСТУП
═══════════════════════════════════════════════════════════════════════════════

LogScope поддерживает dict-подобный доступ к полям:

    scope = LogScope(machine="APM", action="OrderAction")

    scope["machine"]        # → "APM"
    scope["action"]         # → "OrderAction"
    "machine" in scope      # → True
    scope.get("missing")    # → None
    list(scope.keys())      # → ["machine", "action"]

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


class LogScope:
    """
    Scope логирования — хранит координаты вызова в конвейере.

    Лёгкий объект с динамическими атрибутами и dict-подобным доступом.
    Не является pydantic-моделью. Значения передаются как kwargs
    и становятся атрибутами экземпляра.

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

    # Аннотации типов для приватных атрибутов (для mypy и pylint)
    _key_order: list[str]
    _cached_path: str | None

    def __init__(self, **kwargs: Any) -> None:
        """
        Инициализирует scope с произвольным набором именованных аргументов.

        Каждый kwarg становится атрибутом экземпляра. Порядок kwargs
        сохраняется для формирования dotpath.

        Аргументы:
            **kwargs: произвольные именованные аргументы, задающие поля scope.
        """
        for key, value in kwargs.items():
            object.__setattr__(self, key, value)
        object.__setattr__(self, "_key_order", list(kwargs.keys()))
        object.__setattr__(self, "_cached_path", None)

    # ─── dict-подобный доступ ─────────────────────────────────────────

    def __getitem__(self, key: str) -> object:
        """
        Доступ к полю по ключу: scope["field_name"].

        Аргументы:
            key: имя поля.

        Возвращает:
            Значение поля.

        Исключения:
            KeyError: если поле с таким именем не существует.
        """
        try:
            return getattr(self, key)
        except AttributeError:
            raise KeyError(key) from None

    def __contains__(self, key: str) -> bool:
        """Проверка наличия поля: "field_name" in scope."""
        return key in self._key_order

    def get(self, key: str, default: object = None) -> object:
        """Получение значения поля с fallback на default."""
        return getattr(self, key, default)

    def keys(self) -> list[str]:
        """Список имён полей в порядке создания."""
        return list(self._key_order)

    def values(self) -> list[object]:
        """Список значений полей в порядке создания."""
        return [getattr(self, k) for k in self._key_order]

    def items(self) -> list[tuple[str, object]]:
        """Список пар (имя, значение) в порядке создания."""
        return [(k, getattr(self, k)) for k in self._key_order]

    # ─── dotpath и сериализация ───────────────────────────────────────

    def as_dotpath(self) -> str:
        """
        Возвращает все непустые строковые значения, объединённые точками.

        Порядок определяется порядком kwargs при создании.
        Числовые значения (например, nest_level) преобразуются в строку.
        Пустые строки и None пропускаются.
        Результат кешируется после первого вызова.

        Возвращает:
            str — dotpath вида "machine.mode.action.aspect" или пустая строка.
        """
        if self._cached_path is None:
            values = []
            for key in self._key_order:
                val = getattr(self, key, None)
                if val is not None and val != "":
                    values.append(str(val))
            object.__setattr__(self, "_cached_path", ".".join(values))
        return self._cached_path # type: ignore[return-value]

    def to_dict(self) -> dict[str, Any]:
        """
        Возвращает словарь со всеми полями scope в порядке создания.

        Используется для отладки, сериализации и передачи в шаблоны.

        Возвращает:
            dict[str, Any] — словарь {ключ: значение} для всех полей.
        """
        return {key: getattr(self, key) for key in self._key_order}
