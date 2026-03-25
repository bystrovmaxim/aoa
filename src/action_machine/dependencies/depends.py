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
    Декоратор добавляет информацию о зависимостях в атрибут `_depends_info`,
    объявленный в миксине `DependencyGateHost`. При первом вызове
    `get_dependency_gate()` хост собирает `_depends_info`, регистрирует
    каждую зависимость в `DependencyGate` и замораживает шлюз.

    Имя `_depends_info` (с одним подчёркиванием) используется вместо
    `__depends_info` (с двумя), чтобы избежать Python name mangling.

    Декоратор проверяет, что целевой класс наследует DependencyGateHost.
    Если нет — выбрасывает TypeError. Это гарантирует, что декоратор
    не добавляет динамических атрибутов — все поля объявлены в миксине.
"""

from collections.abc import Callable
from typing import Any

from .dependency_gate import DependencyInfo
from .dependency_gate_host import DependencyGateHost


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

    Исключения:
        TypeError: если класс не наследует DependencyGateHost.

    Пример:
        @depends(PaymentService, description="Сервис платежей")
        @depends(NotificationService, description="Сервис уведомлений")
        class CreateOrderAction(BaseAction):
            ...

        # В аспекте:
        payment = box.resolve(PaymentService)
    """

    def decorator(cls: type) -> type:
        # Проверяем, что класс наследует DependencyGateHost,
        # который объявляет атрибут _depends_info как ClassVar.
        if not issubclass(cls, DependencyGateHost):
            raise TypeError(
                f"@depends can only be applied to classes inheriting DependencyGateHost. "
                f"Class {cls.__name__} does not inherit DependencyGateHost. "
                f"Ensure the class inherits from BaseAction or DependencyGateHost directly."
            )

        # _depends_info объявлен в DependencyGateHost как ClassVar[list[DependencyInfo] | None],
        # поэтому после issubclass-проверки mypy знает о его существовании.
        if cls._depends_info is None:
            cls._depends_info = []
        else:
            # Создаём копию, чтобы не мутировать родительский список
            cls._depends_info = list(cls._depends_info)

        cls._depends_info.append(
            DependencyInfo(
                cls=klass,
                factory=factory,
                description=description,
            )
        )

        return cls

    return decorator
