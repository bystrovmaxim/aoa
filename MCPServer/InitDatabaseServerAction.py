# MCPServer/InitDatabaseServerAction.py
import logging
from typing import Dict, Any

from ActionEngine.BaseTransactionAction import BaseTransactionAction
from ActionEngine.TransactionContext import TransactionContext
from ActionEngine.CheckRoles import CheckRoles
from ActionEngine.requires_connection_type import requires_connection_type
from ActionEngine.StringFieldChecker import StringFieldChecker
from ActionEngine.IntFieldChecker import IntFieldChecker
from ActionEngine.InstanceOfChecker import InstanceOfChecker

import psycopg2
from App.InitDatabaseAction import InitDatabaseAction

logger = logging.getLogger(__name__)

@CheckRoles(CheckRoles.ANY, description="Доступен любому аутентифицированному пользователю")
@requires_connection_type(psycopg2.extensions.connection, description="Требуется соединение с PostgreSQL")
class InitDatabaseServerAction(BaseTransactionAction):
    """
    Серверное действие для инициализации таблиц PostgreSQL.
    Ожидает, что в контексте уже есть открытое соединение.
    """

    def _preHandleAspect(self, ctx: TransactionContext, params: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """Подготовка не требуется, возвращаем пустой словарь."""
        return {}

    @StringFieldChecker("schema", description="Результат: имя созданной схемы")
    @InstanceOfChecker("tables_created", expected_class=list, description="Результат: список созданных таблиц")
    def _handleAspect(self, ctx: TransactionContext, params: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """Вызывает InitDatabaseAction с переданным контекстом."""
        action = InitDatabaseAction()
        return action.run(ctx, {})

    @StringFieldChecker("schema", description="Результат после пост-обработки: имя созданной схемы")
    @InstanceOfChecker("tables_created", expected_class=list, description="Результат после пост-обработки: список созданных таблиц")
    def _postHandleAspect(self, ctx: TransactionContext, params: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """Возвращает результат без изменений."""
        return result