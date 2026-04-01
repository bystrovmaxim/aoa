# tests2/domain/test_db_manager.py
"""
Тестовый ресурсный менеджер БД.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Минимальная реализация BaseResourceManager для использования в декораторе
@connection(TestDbManager, key="db") на тестовых Action.

В реальных тестах экземпляр TestDbManager передаётся через
connections={"db": mock_db}, где mock_db — мок с нужным поведением.
TestDbManager нужен только как ТИП для декоратора @connection.

═══════════════════════════════════════════════════════════════════════════════
ИСПОЛЬЗОВАНИЕ
═══════════════════════════════════════════════════════════════════════════════

    # В Action:
    @connection(TestDbManager, key="db", description="Основная БД")
    class FullAction(BaseAction[...]): ...

    # В тесте:
    mock_db = AsyncMock(spec=TestDbManager)
    result = await bench.run(action, params, rollup=False, connections={"db": mock_db})
"""

from action_machine.core.meta_decorator import meta
from action_machine.resource_managers.base_resource_manager import BaseResourceManager


@meta(description="Тестовый менеджер БД для тестов connections")
class TestDbManager(BaseResourceManager):
    """
    Минимальная реализация BaseResourceManager для тестов.

    Используется как тип в декораторе @connection. В тестах заменяется
    моком. Не содержит реальной логики работы с БД.
    """

    def get_wrapper_class(self) -> type["BaseResourceManager"] | None:
        """Обёртка не требуется для тестового менеджера."""
        return None
