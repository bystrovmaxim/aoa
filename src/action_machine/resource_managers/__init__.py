# src/action_machine/resource_managers/__init__.py
"""
Пакет управления ресурсными соединениями ActionMachine.

Содержит базовые абстракции и декораторы для работы с внешними ресурсами
(базы данных, кеши, очереди сообщений и т.д.):

- BaseResourceManager — абстрактный базовый класс для всех менеджеров
  ресурсов. Определяет контракт get_wrapper_class().
- IConnectionManager — интерфейс менеджера соединений с методами
  open/commit/rollback/execute.
- WrapperConnectionManager — прокси-обёртка, запрещающая управление
  транзакциями на вложенных уровнях, но разрешающая выполнение запросов.
- ConnectionGateHost — маркерный миксин, разрешающий применение @connection.
  Класс без этого миксина не может быть целью @connection.
- ConnectionInfo — frozen-датакласс, описывающий одно соединение
  (класс менеджера, ключ, описание).
- connection — декоратор для объявления соединений на классе действия.
- Connections — базовый TypedDict для словаря connections.

Конкретные реализации менеджеров (PostgreSQL, Redis и др.) находятся
в пакете action_machine.contrib и устанавливаются отдельно:

    pip install action-machine[postgres]
    from action_machine.contrib.postgres import PostgresConnectionManager

Типичный поток:
    1. @connection(PostgresManager, key="db") записывает ConnectionInfo
       в cls._connection_info.
    2. ``ConnectionGateHostInspector`` при ``GateCoordinator.build()`` читает
       ``_connection_info`` и формирует facet-снимок / узел графа.
    3. ActionProductMachine._check_connections() сравнивает ключи из scratch
       класса действия с аргументом ``connections``.
    4. Аспекты получают connections["db"] — экземпляр менеджера ресурсов.
"""

from .base_resource_manager import BaseResourceManager
from .connection import ConnectionInfo, connection
from .connection_gate_host import ConnectionGateHost

__all__ = [
    "BaseResourceManager",
    "ConnectionGateHost",
    "ConnectionInfo",
    "connection",
]
