# MCPServer/InitDatabaseServerAction.py
import logging
from typing import Dict, Any

from ActionEngine import (
    TransactionContext,
    CheckRoles,
    InstanceOfChecker,
    StringFieldChecker,
    requires_connection_type,
    BaseTransactionAction)

import psycopg2
from APP.InitDatabaseAction import InitDatabaseAction

logger = logging.getLogger(__name__)

@CheckRoles(["admin"], desc="Доступно только администраторам")
@requires_connection_type(psycopg2.extensions.connection, desc="Требуется соединение с PostgreSQL")
class InitDatabaseServerAction(BaseTransactionAction):
    """
    Серверное действие для инициализации таблиц PostgreSQL.
    Ожидает, что в контексте уже есть открытое соединение.
    """

    def _preHandleAspect(self, ctx: TransactionContext, params: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """Подготовка не требуется, возвращаем пустой словарь."""
        return {}

    @StringFieldChecker("schema", desc="Результат: имя созданной схемы")
    @InstanceOfChecker("tables_created", expected_class=list, desc="Результат: список созданных таблиц")
    def _handleAspect(self, ctx: TransactionContext, params: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """Вызывает InitDatabaseAction с переданным контекстом."""
        action = InitDatabaseAction()
        return action.run(ctx, {})

    @StringFieldChecker("schema", desc="Результат после пост-обработки: имя созданной схемы")
    @InstanceOfChecker("tables_created", expected_class=list, desc="Результат после пост-обработки: список созданных таблиц")
    def _postHandleAspect(self, ctx: TransactionContext, params: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """Возвращает результат без изменений."""
        return result