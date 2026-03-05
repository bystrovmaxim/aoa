import logging
from typing import List, Optional, Dict, Any

from ActionEngine.BaseSimpleAction import BaseSimpleAction
from ActionEngine.Context import Context
from ActionEngine.TransactionContext import TransactionContext
from ActionEngine.PostgresConnectionManager import PostgresConnectionManager
from ActionEngine.CheckRoles import CheckRoles
from ActionEngine.IntFieldChecker import IntFieldChecker
from ActionEngine.StringFieldChecker import StringFieldChecker
from ActionEngine.InstanceOfChecker import InstanceOfChecker

from App.DeleteSnapshotPostgressAction import DeleteSnapshotProgressAction

logger = logging.getLogger(__name__)


@CheckRoles(CheckRoles.ANY, desc="Доступен любому аутентифицированному пользователю")
@StringFieldChecker("snapshot_date", required=True, not_empty=True, desc="Входной параметр: дата снимка (строка YYYY-MM-DD)")
@InstanceOfChecker("tables", expected_class=list, required=True, desc="Входной параметр: список имён таблиц для очистки")
@StringFieldChecker("schema", required=False, not_empty=True, desc="Входной параметр: имя схемы (по умолчанию youtrack)")
@StringFieldChecker("pg_host", required=True, desc="Входной параметр: хост PostgreSQL (из окружения)")
@IntFieldChecker("pg_port", required=True, desc="Входной параметр: порт PostgreSQL (из окружения)")
@StringFieldChecker("pg_db", required=True, desc="Входной параметр: имя базы данных PostgreSQL")
@StringFieldChecker("pg_user", required=True, desc="Входной параметр: пользователь PostgreSQL")
@StringFieldChecker("pg_password", required=True, desc="Входной параметр: пароль PostgreSQL")
class DeleteSnapshotServerAction(BaseSimpleAction):
    """
    Оркестрирующее действие для удаления снимков за указанную дату из заданных таблиц.
    Параметры подключения к PostgreSQL передаются через входные параметры (обычно берутся из окружения в фасаде).
    """

    def _preHandleAspect(self, ctx: Context, params: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """Создаёт менеджер соединения PostgreSQL."""
        db_params = {
            "host": params["pg_host"],
            "port": params["pg_port"],
            "dbname": params["pg_db"],
            "user": params["pg_user"],
            "password": params["pg_password"],
        }
        mgr = PostgresConnectionManager(db_params)
        mgr.open()
        tx_ctx = TransactionContext(base_ctx=ctx, connection=mgr.connection)
        return {"manager": mgr, "tx_ctx": tx_ctx}

    @IntFieldChecker("deleted_total", min_value=0, desc="Результат: общее количество удалённых записей")
    def _handleAspect(self, ctx: Context, params: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """Вызывает DeleteSnapshotAction с переданными параметрами."""
        tx_ctx = result["tx_ctx"]
        action = DeleteSnapshotProgressAction()
        delete_params = {
            "snapshot_date": params["snapshot_date"],
            "tables": params["tables"],
            "schema": params.get("schema", "youtrack"),
        }
        return action.run(tx_ctx, delete_params)

    @IntFieldChecker("deleted_total", min_value=0, desc="Результат после пост-обработки: общее количество удалённых записей")
    def _postHandleAspect(self, ctx: Context, params: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """Фиксирует транзакцию и возвращает результат."""
        mgr = result.get("manager")
        if mgr:
            mgr.commit()
        # Убираем служебные ключи
        result.pop("manager", None)
        result.pop("tx_ctx", None)
        return result

    def _onErrorAspect(self, ctx: Context, params: Dict[str, Any], result: Dict[str, Any], error: Exception) -> None:
        """При ошибке откатывает транзакцию."""
        mgr = result.get("manager")
        if mgr:
            try:
                mgr.rollback()
            except Exception:
                pass
        logger.error(f"Ошибка в DeleteSnapshotServerAction: {error}")