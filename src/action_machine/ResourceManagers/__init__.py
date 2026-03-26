# src/action_machine/ResourceManagers/__init__.py
"""
Пакет управления ресурсными соединениями ActionMachine.

Содержит:
- BaseResourceManager — абстрактный базовый класс для всех менеджеров
  ресурсов (PostgreSQL, Redis, RabbitMQ и т.д.). Определяет контракт
  connect/disconnect/health_check.
- ConnectionGateHost — маркерный миксин, разрешающий применение @connection.
  Класс без этого миксина не может быть целью @connection.
- ConnectionInfo — frozen-датакласс, описывающий одно соединение
  (класс менеджера, ключ, описание).
- connection — декоратор для объявления соединений на классе действия.

Типичный поток:
    1. @connection(PostgresManager, key="db") записывает ConnectionInfo
       в cls._connection_info.
    2. MetadataBuilder.build(cls) читает _connection_info →
       ClassMetadata.connections (tuple[ConnectionInfo, ...]).
    3. ActionProductMachine._check_connections() читает
       metadata.get_connection_keys() и сравнивает с фактическими ключами
       из аргумента connections.
    4. Аспекты получают connections["db"] — экземпляр PostgresManager.
"""

from .BaseResourceManager import BaseResourceManager
from .connection import ConnectionInfo, connection
from .connection_gate_host import ConnectionGateHost

__all__ = [
    "BaseResourceManager",
    "ConnectionGateHost",
    "ConnectionInfo",
    "connection",
]