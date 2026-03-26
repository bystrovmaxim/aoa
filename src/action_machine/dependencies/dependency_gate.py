# src/action_machine/dependencies/dependency_gate.py
"""
DependencyGate — шлюз для управления зависимостями действий.

Хранит информацию о зависимостях, объявленных через декоратор @depends.
Каждая зависимость описывается классом и описанием. Шлюз обеспечивает
быстрый доступ по классу зависимости и сохраняет порядок регистрации.

После завершения сборки (в __init_subclass__ хоста) шлюз замораживается,
и любые попытки регистрации или удаления вызывают RuntimeError.

Жизненный цикл:
    1. Создаётся в DependencyGateHost.__init_subclass__.
    2. Заполняется через register() на основе cls._depends_info.
    3. Замораживается через freeze().
    4. Читается потребителями через get_by_class(), get_all_classes(),
       get_components().
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from action_machine.core.base_gate import BaseGate


@dataclass(frozen=True)
class DependencyInfo:
    """
    Неизменяемая информация об одной зависимости.

    Атрибуты:
        cls: класс зависимости (тип, который будет запрошен через box.resolve).
        factory: опциональная фабрика для создания экземпляра.
                 Если None, используется конструктор по умолчанию.
        description: текстовое описание зависимости (для документации
                     и интроспекции).
    """
    cls: type
    factory: Callable[[], Any] | None = None
    description: str = ""


class DependencyGate(BaseGate[DependencyInfo]):
    """
    Шлюз для управления зависимостями.

    Внутреннее хранение:
        _deps: dict[type, DependencyInfo] — словарь для быстрого доступа по классу.
               Сохраняет порядок вставки (Python 3.7+).
        _frozen: bool — флаг заморозки. После freeze() изменения запрещены.
    """

    def __init__(self) -> None:
        """Инициализирует пустой шлюз зависимостей."""
        self._deps: dict[type, DependencyInfo] = {}
        self._frozen: bool = False

    def _check_frozen(self) -> None:
        """Проверяет, не заморожен ли шлюз. Если заморожен — RuntimeError."""
        if self._frozen:
            raise RuntimeError("DependencyGate заморожен, изменения запрещены.")

    def register(self, _component: DependencyInfo, **metadata: Any) -> DependencyInfo:
        """
        Регистрирует зависимость.

        Если зависимость с таким же классом уже зарегистрирована — ValueError.

        Аргументы:
            _component: информация о зависимости.
            **metadata: не используется, оставлен для совместимости с BaseGate.

        Возвращает:
            Зарегистрированный компонент.

        Исключения:
            RuntimeError: шлюз заморожен.
            ValueError: зависимость с таким классом уже существует.
        """
        self._check_frozen()
        if _component.cls in self._deps:
            raise ValueError(
                f"Зависимость для класса {_component.cls.__name__} уже зарегистрирована."
            )
        self._deps[_component.cls] = _component
        return _component

    def unregister(self, _component: DependencyInfo) -> None:
        """
        Удаляет зависимость по ссылке.

        Удаляет только если сохранённый объект совпадает по ссылке (is)
        с переданным. Это защита от случайного удаления чужой зависимости.

        Аргументы:
            _component: информация о зависимости для удаления.

        Исключения:
            RuntimeError: шлюз заморожен.
        """
        self._check_frozen()
        if _component.cls in self._deps and self._deps[_component.cls] is _component:
            del self._deps[_component.cls]

    def get_components(self) -> list[DependencyInfo]:
        """
        Возвращает список всех зарегистрированных зависимостей в порядке регистрации.

        Возвращаемый список — копия, внешние модификации не влияют на шлюз.

        Возвращает:
            Список объектов DependencyInfo.
        """
        return list(self._deps.values())

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

        Возвращаемый список — копия.

        Возвращает:
            Список классов.
        """
        return list(self._deps.keys())

    def has_dependency(self, cls: type) -> bool:
        """
        Проверяет, зарегистрирована ли зависимость для данного класса.

        Аргументы:
            cls: класс зависимости.

        Возвращает:
            True если зависимость зарегистрирована, False иначе.
        """
        return cls in self._deps

    def freeze(self) -> None:
        """
        Замораживает шлюз, запрещая дальнейшие изменения.

        Вызывается после завершения сбора зависимостей в __init_subclass__.
        Повторный вызов безопасен (идемпотентен).
        """
        self._frozen = True

    @property
    def is_frozen(self) -> bool:
        """Возвращает True если шлюз заморожен."""
        return self._frozen
