# src/action_machine/dependencies/dependency_factory.py
"""
DependencyFactory – фабрика для создания экземпляров зависимостей действий.

Фабрика создаётся для каждого класса действия и кэширует созданные экземпляры.
Она использует DependencyGate для получения информации о зависимостях (класс,
фабрика, описание). Фабрика не хранит внешние ресурсы – они передаются через
ToolsBox в момент выполнения.

Изменения (этап миграции на шлюзы):
- Конструктор принимает DependencyGate вместо deps_info.
- Метод resolve() использует gate.get_by_class() для получения информации.
- Сохранена обратная совместимость с инициализацией через deps_info (временный период).
"""

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

    def __init__(self, gate: DependencyGate) -> None:
        """
        Инициализирует фабрику.

        Аргументы:
            gate: DependencyGate, содержащий информацию о зависимоциях.
                  Может быть получен через action.get_dependency_gate().
        """
        self._gate: DependencyGate = gate
        self._instances: dict[type, Any] = {}

    # Временный конструктор для обратной совместимости с устаревшим кодом
    @classmethod
    def from_deps_info(cls, deps_info: list[dict[str, Any]]) -> "DependencyFactory":
        """
        Создаёт фабрику из старого формата deps_info (для обратной совместимости).

        Этот метод будет удалён после полного перехода на шлюзы.

        Аргументы:
            deps_info: список словарей с ключами 'class', 'factory', 'description'.

        Возвращает:
            DependencyFactory, заполненный данными.
        """
        gate = DependencyGate()
        for info in deps_info:
            dep_info = DependencyInfo(
                cls=info["class"],
                factory=info.get("factory"),
                description=info.get("description", "")
            )
            gate.register(dep_info)
        gate.freeze()
        return cls(gate)

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
        info = self._gate.get_by_class(klass)
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