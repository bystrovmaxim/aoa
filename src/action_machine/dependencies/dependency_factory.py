"""
DependencyFactory – фабрика для создания экземпляров зависимостей действий.

Фабрика создаётся для каждого класса действия и кэширует созданные экземпляры.
Она использует DependencyGate для получения информации о зависимостях (класс,
фабрика, описание). Фабрика не хранит внешние ресурсы – они передаются через
ToolsBox в момент выполнения.

Поддерживает два формата инициализации:
1. DependencyGate — основной формат (из шлюза действия).
2. list[dict] — обратная совместимость (для тестов и старого кода).
   Каждый dict: {"class": type, "factory": callable|None, "description": str}
"""

from collections.abc import Callable
from typing import Any

from .dependency_gate import DependencyGate, DependencyInfo


class DependencyFactory:
    """
    Фабрика зависимостей для действий.

    Создаёт и кэширует экземпляры зависимостей, объявленных через @depends.
    Для каждого класса зависимости, запрошенного через resolve(), фабрика
    либо возвращает закэшированный экземпляр, либо создаёт новый через
    фабрику или конструктор по умолчанию.

    Атрибуты:
        _gate: DependencyGate – шлюз с информацией о зависимостях.
        _instances: dict[type, Any] – кэш созданных экземпляров.
    """

    def __init__(self, gate: DependencyGate | list[dict[str, Any]]) -> None:
        """
        Инициализирует фабрику.

        Аргументы:
            gate: DependencyGate, содержащий информацию о зависимостях,
                  или list[dict] для обратной совместимости.
                  Каждый dict в списке: {"class": type, "factory": callable|None, "description": str}
        """
        if isinstance(gate, DependencyGate):
            self._gate: DependencyGate = gate
        elif isinstance(gate, list):
            # Обратная совместимость: конвертируем list[dict] в DependencyGate
            self._gate = self._gate_from_list(gate)
        else:
            raise TypeError(
                f"DependencyFactory expects DependencyGate or list[dict], got {type(gate).__name__}"
            )
        self._instances: dict[type, Any] = {}

    @staticmethod
    def _gate_from_list(deps_info: list[dict[str, Any]]) -> DependencyGate:
        """
        Создаёт DependencyGate из списка словарей (обратная совместимость).

        Аргументы:
            deps_info: список словарей, каждый содержит:
                - "class": тип зависимости
                - "factory": опциональная фабрика (callable или None)
                - "description": описание (строка)

        Возвращает:
            Заполненный и замороженный DependencyGate.
        """
        gate = DependencyGate()
        for info_dict in deps_info:
            info = DependencyInfo(
                cls=info_dict["class"],
                factory=info_dict.get("factory"),
                description=info_dict.get("description", ""),
            )
            gate.register(info)
        gate.freeze()
        return gate

    def resolve(self, klass: type) -> Any:
        """
        Возвращает экземпляр зависимости указанного класса.

        Если экземпляр уже создан, возвращается из кэша.
        Иначе создаётся новый через фабрику (если задана) или конструктор по умолчанию.

        Аргументы:
            klass: класс зависимости.

        Возвращает:
            Экземпляр зависимости.

        Исключения:
            ValueError: если зависимость не объявлена в шлюзе.
        """
        # Проверяем кэш
        if klass in self._instances:
            return self._instances[klass]

        # Получаем информацию из шлюза
        info: DependencyInfo | None = self._gate.get_by_class(klass)
        if info is None:
            raise ValueError(
                f"Dependency {klass.__name__} not declared in @depends. "
                f"Available: {self._gate.get_all_classes()}"
            )

        # Создаём экземпляр
        if info.factory:
            instance = info.factory()
        else:
            instance = klass()

        # Кэшируем
        self._instances[klass] = instance
        return instance
