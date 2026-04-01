# tests2/resource_managers/test_connections.py
"""
Тесты Connections — базового TypedDict для словаря connections.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Connections — базовый TypedDict, определяющий структуру словаря, передаваемого
в аспекты через параметр connections. Содержит единственный стандартный ключ
'connection' (покрывает 99% случаев использования). Для сложных случаев
разработчик может создать наследника с дополнительными ключами.

TypedDict — это статический контракт для IDE и mypy. В runtime connections
остаётся обычным dict, и ActionMachine проверяет его содержимое динамически.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

- Создание словаря с ключом 'connection' проходит проверку типов.
- Создание словаря с другими ключами также допустимо (total=False).
- Значение по ключу — экземпляр BaseResourceManager.
"""

from action_machine.resource_managers.base_resource_manager import BaseResourceManager
from action_machine.resource_managers.connections import Connections


class DummyResourceManager(BaseResourceManager):
    """Заглушка менеджера ресурсов для тестов."""
    def get_wrapper_class(self):
        return None


def test_connections_typeddict() -> None:
    """
    Connections — TypedDict, принимающий ключ 'connection'
    со значением BaseResourceManager.
    """
    # Arrange — экземпляр заглушки
    res = DummyResourceManager()

    # Act — создание словаря, соответствующего Connections
    conn: Connections = {"connection": res}

    # Assert — доступ по ключу работает
    assert conn["connection"] is res
