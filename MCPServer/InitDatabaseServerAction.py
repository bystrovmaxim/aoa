import logging
from typing import Dict, Any

from ActionEngine.BaseSimpleAction import BaseSimpleAction
from ActionEngine.Context import Context
from ActionEngine.TransactionContext import TransactionContext
from ActionEngine.PostgresConnectionManager import PostgresConnectionManager
from ActionEngine.CheckRoles import CheckRoles
from ActionEngine.StringFieldChecker import StringFieldChecker
from ActionEngine.IntFieldChecker import IntFieldChecker
from ActionEngine.InstanceOfChecker import InstanceOfChecker

from App.InitDatabaseAction import InitDatabaseAction

logger = logging.getLogger(__name__)


@CheckRoles(CheckRoles.ANY)
@StringFieldChecker("pg_host", required=True)
@IntFieldChecker("pg_port", required=True)
@StringFieldChecker("pg_db", required=True)
@StringFieldChecker("pg_user", required=True)
@StringFieldChecker("pg_password", required=True)
class InitDatabaseServerAction(BaseSimpleAction):
    """
    Серверное действие для инициализации таблиц PostgreSQL.
    Параметры:
        pg_host, pg_port, pg_db, pg_user, pg_password.
    """

    def _preHandleAspect(self, ctx: Context, params: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """Создаёт менеджер соединения."""
        db_params = {
            "host": params["pg_host"],
            "port": params["pg_port"],
            "dbname": params["pg_db"],
            "user": params["pg_user"],
            "password": params["pg_password"],
        }
        mgr = PostgresConnectionManager(db_params)
        mgr.open()
        # Сохраняем менеджер в result для передачи дальше
        return {"manager": mgr}

    @StringFieldChecker("schema")
    @InstanceOfChecker("tables_created", expected_class=list)
    def _handleAspect(self, ctx: Context, params: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """Вызывает InitDatabaseAction и добавляет менеджер в результат."""
        mgr = result["manager"]
        tx_ctx = TransactionContext(base_ctx=ctx, connection=mgr.connection)
        action = InitDatabaseAction()
        db_result = action.run(tx_ctx, {})
        # Добавляем менеджер в результат, чтобы он был доступен в _postHandleAspect
        db_result["manager"] = mgr
        return db_result

    @StringFieldChecker("schema")                     # проверяем, что schema осталась
    @InstanceOfChecker("tables_created", expected_class=list)  # проверяем tables_created
    def _postHandleAspect(self, ctx: Context, params: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """Фиксирует транзакцию, удаляет менеджер и возвращает чистый результат."""
        mgr = result.get("manager")
        if mgr:
            mgr.commit()
        # Удаляем служебное поле manager перед возвратом
        result.pop("manager", None)
        return result
    
    def _onErrorAspect(self, ctx: Context, params: Dict[str, Any], result: Dict[str, Any], error: Exception) -> None:
        """При ошибке откатывает транзакцию PostgreSQL."""
        mgr = result.get("manager")
        if mgr:
            mgr.rollback()
        logger.error(f"Ошибка в InitDatabaseServerAction: {error}")