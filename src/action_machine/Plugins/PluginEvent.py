"""
Dataclass для передачи данных события в плагины.
Содержит всю информацию о текущем событии выполнения действия.
"""

from dataclasses import dataclass

from action_machine.Context.context import Context
from action_machine.Core.DependencyFactory import DependencyFactory
from action_machine.Core.Protocols import ReadableDataProtocol, WritableDataProtocol


@dataclass
class PluginEvent:
    """
    Контейнер для всех данных, передаваемых в обработчик плагина.
    Создаётся на каждое событие и передаётся в методы плагинов,
    помеченные декоратором @on.

    Все поля предназначены только для чтения; изменение объекта
    не влияет на выполнение действия (плагины read-only).
    """

    event_name: str
    """Имя события (например, 'global_start', 'before:validate', 'after:save', 'global_finish')."""

    action_name: str
    """Полное имя класса действия (включая модуль), для которого произошло событие."""

    params: ReadableDataProtocol
    """Входные параметры действия (неизменяемый объект, соответствующий ReadableDataProtocol)."""

    state_aspect: dict[str, object] | None
    """
    Состояние (state) на момент события.
    Для before-событий – состояние до выполнения аспекта.
    Для after-событий – состояние после выполнения аспекта.
    Для global_start и global_finish может быть None или содержать финальное состояние.
    Всегда dict (или None), так как state теперь строго TypedDict/словарь.
    """

    is_summary: bool
    """Флаг, указывающий, относится ли событие к summary-аспекту (если применимо)."""

    deps: DependencyFactory
    """Фабрика зависимостей для текущего выполнения действия (позволяет получать ресурсы)."""

    context: Context
    """Контекст выполнения (информация о пользователе, запросе, окружении)."""

    result: WritableDataProtocol | None
    """
    Результат выполнения действия (для событий global_finish).
    Для остальных событий – None.
    """

    duration: float | None
    """
    Длительность выполнения в секундах.
    Для after-событий – время выполнения соответствующего аспекта.
    Для global_finish – общее время выполнения действия.
    Для других событий – None.
    """

    nest_level: int
    """Уровень вложенности вызова действия (0 для корневого действия, 1 для дочернего и т.д.)."""
