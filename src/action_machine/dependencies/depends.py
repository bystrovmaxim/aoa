# src/action_machine/dependencies/depends.py
"""
Декоратор @depends для объявления зависимостей действия.

Этот декоратор используется на уровне класса действия для декларации того,
какие зависимости (сервисы, репозитории, другие действия) требуются действию.
ActionMachine будет автоматически создавать и предоставлять эти зависимости
через ToolsBox.resolve().

Особенности:
- Может использоваться несколько раз для одного действия.
- Зависимости не наследуются (каждый класс определяет свои).
- Поддерживает опциональную фабрику для кастомного создания экземпляра.

Архитектурная роль:
    Декоратор добавляет информацию о зависимостях в два места:
        1. Атрибут `_dependencies` — для обратной совместимости со старым кодом.
        2. Временный список `_depends_info` — для ленивого сбора в `DependencyGateHost`.

    При первом вызове `get_dependency_gate()` хост собирает `_depends_info`,
    регистрирует каждую зависимость в `DependencyGate` и замораживает шлюз.

    Имя `_depends_info` (с одним подчёркиванием) используется вместо
    `__depends_info` (с двумя), чтобы избежать Python name mangling,
    который превращает `__attr` в `_ClassName__attr` и делает атрибут
    недоступным через `getattr(cls, '__depends_info')`.

    Параллельное существование двух механизмов (старый `_dependencies` и новый
    `_depends_info`) обеспечивает плавную миграцию. После полного перехода на
    шлюзы старый атрибут будет удалён.
"""

from collections.abc import Callable
from typing import Any

from .dependency_gate import DependencyInfo


def depends(
    klass: type,
    *,
    description: str = "",
    factory: Callable[[], Any] | None = None,
) -> Callable[[type], type]:
    """
    Декоратор для объявления зависимости действия от любого класса.

    Может применяться несколько раз для одного действия. Каждый вызов
    добавляет одну зависимость. Порядок применения декораторов определяет
    порядок зависимостей (хотя обычно он не важен).

    Аргументы:
        klass: класс зависимости (может быть Action, сервис, репозиторий и т.д.).
        description: описание зависимости (для документации).
        factory: опциональная фабрика для создания экземпляра.
                 Если не указана, используется конструктор по умолчанию.

    Возвращает:
        Декоратор, который добавляет информацию о зависимости в класс.

    Пример:
        @depends(PaymentService, description="Сервис платежей")
        @depends(NotificationService, description="Сервис уведомлений")
        class CreateOrderAction(BaseAction):
            ...

        # В аспекте:
        payment = box.resolve(PaymentService)
    """

    def decorator(cls: type) -> type:
        # --- Старый механизм (для обратной совместимости) ---
        # Создаём НОВЫЙ список, копируя родительский (если есть)
        deps = list(getattr(cls, "_dependencies", []))
        deps.append(
            {
                "class": klass,
                "description": description,
                "factory": factory,
            }
        )
        cls._dependencies = deps  # type: ignore[attr-defined]

        # --- Новый механизм (для шлюза) ---
        # Используем _depends_info (одно подчёркивание), чтобы избежать
        # Python name mangling (которое превращает __attr в _ClassName__attr).
        if not hasattr(cls, "_depends_info") or cls._depends_info is None:
            cls._depends_info = []  # type: ignore[attr-defined]
        else:
            # Создаём копию, чтобы не мутировать родительский список
            cls._depends_info = list(cls._depends_info)  # type: ignore[attr-defined]

        cls._depends_info.append(  # type: ignore[attr-defined]
            DependencyInfo(
                cls=klass,
                factory=factory,
                description=description,
            )
        )

        return cls

    return decorator
