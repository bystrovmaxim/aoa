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
        2. Временный список `__depends_info` — для сбора в `DependencyGateHost`.

    При создании класса (в `__init_subclass__`) `DependencyGateHost` собирает
    `__depends_info`, регистрирует каждую зависимость в `DependencyGate` и затем
    удаляет временный атрибут. После этого шлюз замораживается.

    Фабрика зависимостей (`DependencyFactory`) использует `DependencyGate` для
    получения информации о зависимостях.

    Параллельное существование двух механизмов (старый `_dependencies` и новый
    `__depends_info`) обеспечивает плавную миграцию. После полного перехода на
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
        # mypy не знает о существовании атрибута _dependencies,
        # поэтому добавляем игнорирование.
        cls._dependencies = deps  # type: ignore[attr-defined]

        # --- Новый механизм (для шлюза) ---
        # Добавляем временную информацию, которая будет собрана в __init_subclass__
        if not hasattr(cls, "__depends_info"):
            # mypy не знает о __depends_info — игнорируем
            cls.__depends_info = []  # type: ignore[attr-defined]
        cls.__depends_info.append(  # type: ignore[attr-defined]
            DependencyInfo(
                cls=klass,
                factory=factory,
                description=description,
            )
        )

        return cls

    return decorator