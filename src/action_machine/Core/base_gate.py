# action_machine/Core/base_gate.py

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

T = TypeVar('T')

class BaseGate(ABC, Generic[T]):
    """
    Абстрактный базовый класс для всех шлюзов в ActionMachine.

    Шлюз — это контейнер, который хранит компоненты определённого типа.
    Он предоставляет единый интерфейс для регистрации, удаления и получения
    компонентов. Этот дизайн заменяет магические атрибуты явным,
    типобезопасным и тестируемым API.

    Параметр типа:
        T: тип компонента, которым управляет шлюз.
    """

    @abstractmethod
    def register(self, component: T, **metadata) -> T:
        """
        Зарегистрировать компонент в шлюзе.

        Аргументы:
            component: регистрируемый компонент (типа T).
            **metadata: дополнительные метаданные (описание, тип и т.п.).

        Возвращает:
            Зарегистрированный компонент (для удобства цепочек).
        """
        pass

    @abstractmethod
    def unregister(self, component: T) -> None:
        """Удалить компонент из шлюза."""
        pass

    @abstractmethod
    def get_components(self) -> list[T]:
        """Вернуть все зарегистрированные компоненты (порядок может быть значимым)."""
        pass