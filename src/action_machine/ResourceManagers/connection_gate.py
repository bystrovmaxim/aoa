"""
Шлюз для управления объявленными соединениями (ресурсными менеджерами) действия.

Соединения объявляются с помощью декоратора @connection на уровне класса действия.
Каждое соединение характеризуется:
- ключом (строковым идентификатором, под которым оно будет доступно в словаре connections),
- классом ресурсного менеджера (наследник BaseResourceManager),
- опциональным описанием.

Шлюз обеспечивает хранение информации о соединениях в порядке объявления и быстрый доступ
по ключу. После завершения сборки класса (в __init_subclass__) шлюз замораживается,
и любые попытки регистрации или удаления вызывают RuntimeError.
"""

from dataclasses import dataclass
from typing import Any

from action_machine.Core.base_gate import BaseGate
from action_machine.ResourceManagers.BaseResourceManager import BaseResourceManager


@dataclass(frozen=True)
class ConnectionInfo:
    """
    Неизменяемая информация об одном объявленном соединении.

    Атрибуты:
        key: строковый ключ, по которому соединение будет доступно в словаре connections.
        klass: класс ресурсного менеджера (наследник BaseResourceManager).
        description: текстовое описание соединения (для документации).
    """
    key: str
    klass: type[BaseResourceManager]
    description: str


class ConnectionGate(BaseGate[ConnectionInfo]):
    """
    Шлюз для управления соединениями действия.

    Внутреннее хранение:
        _connections: dict[str, ConnectionInfo] – словарь для быстрого доступа по ключу.
                      Сохраняет порядок вставки (Python 3.7+).
        _frozen: bool – флаг, указывающий, что шлюз заморожен и не может быть изменён.
    """

    def __init__(self) -> None:
        """Инициализирует пустой шлюз соединений."""
        self._connections: dict[str, ConnectionInfo] = {}
        self._frozen: bool = False

    def _check_frozen(self) -> None:
        """Проверяет, не заморожен ли шлюз. Если заморожен – выбрасывает RuntimeError."""
        if self._frozen:
            raise RuntimeError("ConnectionGate is frozen, cannot modify")

    def register(self, _component: ConnectionInfo, **metadata: Any) -> ConnectionInfo:
        """
        Регистрирует информацию о соединении.

        Если соединение с таким же ключом уже зарегистрировано, выбрасывает ValueError.

        Аргументы:
            _component: информация о соединении.
            **metadata: не используется, но оставлен для совместимости с BaseGate.

        Возвращает:
            Зарегистрированный компонент.

        Исключения:
            RuntimeError: если шлюз уже заморожен.
            ValueError: если соединение с таким ключом уже существует.
        """
        self._check_frozen()
        if _component.key in self._connections:
            raise ValueError(f"Connection with key '{_component.key}' already registered")
        self._connections[_component.key] = _component
        return _component

    def unregister(self, _component: ConnectionInfo) -> None:
        """
        Удаляет информацию о соединении по ключу.

        Поскольку после заморозки изменения запрещены, метод выбрасывает исключение,
        если шлюз уже заморожен. В противном случае удаляет по ключу.

        Аргументы:
            _component: информация о соединении для удаления.

        Исключения:
            RuntimeError: если шлюз уже заморожен.
        """
        self._check_frozen()
        # Удаляем по ключу, так как ссылка component может не совпадать с сохранённой,
        # но ключ однозначен.
        if _component.key in self._connections and self._connections[_component.key] is _component:
            del self._connections[_component.key]

    def get_components(self) -> list[ConnectionInfo]:
        """
        Возвращает список всех зарегистрированных соединений в порядке регистрации.

        Возвращаемый список является копией, чтобы предотвратить внешние модификации.

        Возвращает:
            Список объектов ConnectionInfo.
        """
        return list(self._connections.values())

    # -------------------- Дополнительные методы для удобства --------------------

    def get_by_key(self, key: str) -> ConnectionInfo | None:
        """
        Возвращает информацию о соединении по ключу.

        Аргументы:
            key: строковый ключ.

        Возвращает:
            ConnectionInfo или None, если не найдено.
        """
        return self._connections.get(key)

    def get_all_keys(self) -> list[str]:
        """
        Возвращает список всех ключей соединений в порядке регистрации.

        Возвращаемый список является копией.

        Возвращает:
            Список ключей.
        """
        return list(self._connections.keys())

    def freeze(self) -> None:
        """
        Замораживает шлюз, запрещая дальнейшие изменения.

        Вызывается после завершения сбора соединений в __init_subclass__.
        """
        self._frozen = True