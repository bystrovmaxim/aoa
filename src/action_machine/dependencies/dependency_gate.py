# src/action_machine/dependencies/dependency_gate.py
"""
DependencyGate – шлюз для управления зависимостями действий.

Хранит информацию о зависимостях, объявленных через декоратор @depends.
Каждая зависимость описывается классом, опциональной фабрикой и описанием.
Шлюз обеспечивает быстрый доступ по классу зависимости и сохраняет порядок
регистрации (важен для некоторых потребителей, хотя обычно не требуется).

После завершения сборки (в __init_subclass__ действия) шлюз замораживается,
и любые попытки регистрации или удаления вызывают RuntimeError.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from action_machine.Core.base_gate import BaseGate


@dataclass(frozen=True)
class DependencyInfo:
    """
    Неизменяемая информация об одной зависимости.

    Атрибуты:
        cls: класс зависимости (тип, который будет запрошен через resolve).
        factory: опциональная фабрика для создания экземпляра.
                 Если None, используется конструктор по умолчанию.
        description: текстовое описание зависимости (для документации).
    """
    cls: type
    factory: Callable[[], Any] | None
    description: str


class DependencyGate(BaseGate[DependencyInfo]):
    """
    Шлюз для управления зависимостями.

    Внутреннее хранение:
        _deps: dict[type, DependencyInfo] – словарь для быстрого доступа по классу.
                Сохраняет порядок вставки (Python 3.7+).
        _frozen: bool – флаг, указывающий, что шлюз заморожен и не может быть изменён.
    """

    def __init__(self) -> None:
        """Инициализирует пустой шлюз зависимостей."""
        self._deps: dict[type, DependencyInfo] = {}
        self._frozen: bool = False

    def _check_frozen(self) -> None:
        """Проверяет, не заморожен ли шлюз. Если заморожен – выбрасывает RuntimeError."""
        if self._frozen:
            raise RuntimeError("DependencyGate is frozen, cannot modify")

    def register(self, _component: DependencyInfo, **metadata: Any) -> DependencyInfo:
        """
        Регистрирует зависимость.

        Если зависимость с таким же классом уже зарегистрирована, выбрасывает ValueError.

        Аргументы:
            _component: информация о зависимости.
            **metadata: не используется, но оставлен для совместимости с BaseGate.

        Возвращает:
            Зарегистрированный компонент.

        Исключения:
            RuntimeError: если шлюз уже заморожен.
            ValueError: если зависимость с таким классом уже существует.
        """
        self._check_frozen()
        if _component.cls in self._deps:
            raise ValueError(f"Dependency for class {_component.cls.__name__} already registered")
        self._deps[_component.cls] = _component
        return _component

    def unregister(self, _component: DependencyInfo) -> None:
        """
        Удаляет зависимость по ссылке.

        Поскольку после заморозки изменения запрещены, метод выбрасывает исключение,
        если шлюз уже заморожен. В противном случае удаляет по ключу.

        Аргументы:
            _component: информация о зависимости для удаления.

        Исключения:
            RuntimeError: если шлюз уже заморожен.
        """
        self._check_frozen()
        # Удаляем по ключу, так как ссылка component может не совпадать с сохранённой,
        # но ключ однозначен.
        if _component.cls in self._deps and self._deps[_component.cls] is _component:
            del self._deps[_component.cls]

    def get_components(self) -> list[DependencyInfo]:
        """
        Возвращает список всех зарегистрированных зависимостей в порядке регистрации.

        Возвращаемый список является копией, чтобы предотвратить внешние модификации.

        Возвращает:
            Список объектов DependencyInfo.
        """
        return list(self._deps.values())

    # -------------------- Дополнительные методы для удобства --------------------

    def get_by_class(self, cls: type) -> DependencyInfo | None:
        """
        Возвращает информацию о зависимости по классу.

        Аргументы:
            cls: класс зависимости.

        Возвращает:
            DependencyInfo или None, если не найдено.
        """
        return self._deps.get(cls)

    def get_all_classes(self) -> list[type]:
        """
        Возвращает список всех классов зависимостей в порядке регистрации.

        Возвращаемый список является копией.

        Возвращает:
            Список классов.
        """
        return list(self._deps.keys())

    def freeze(self) -> None:
        """
        Замораживает шлюз, запрещая дальнейшие изменения.

        Вызывается после завершения сбора зависимостей в __init_subclass__.
        """
        self._frozen = True