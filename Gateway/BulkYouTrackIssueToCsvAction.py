# MCPServer/BulkYouTrackIssueToCsvAction.py
import logging
from typing import Optional, Dict, Any, List, Tuple

from ActionEngine.BaseSimpleAction import BaseSimpleAction
from ActionEngine.Context import Context
from ActionEngine.TransactionContext import TransactionContext
from ActionEngine.CsvConnectionManager import CsvConnectionManager
from ActionEngine.CheckRoles import CheckRoles
from ActionEngine.IntFieldChecker import IntFieldChecker
from ActionEngine.InstanceOfChecker import InstanceOfChecker
from ActionEngine.StringFieldChecker import StringFieldChecker

from APP.FetchIssuesFromYouTrackAction import FetchIssuesFromYouTrackAction
from APP.YouTrackIssuesCSVSaver import YouTrackIssuesCSVSaver

logger = logging.getLogger(__name__)


@CheckRoles(CheckRoles.ANY, desc="Доступен любому аутентифицированному пользователю")
@IntFieldChecker("page_size", min_value=1, max_value=5000, desc="Входной параметр: размер страницы (целое от 1 до 500)")
@StringFieldChecker("user_stories_file", required=False, not_empty=True, desc="Входной параметр: путь к CSV-файлу для историй (опционально)")
@StringFieldChecker("tasks_file", required=False, not_empty=True, desc="Входной параметр: путь к CSV-файлу для задач (опционально)")
@StringFieldChecker("project_id", required=False, not_empty=True, desc="Входной параметр: идентификатор проекта (опционально)")
@StringFieldChecker("base_url", required=True, desc="Входной параметр: URL YouTrack (обязательная строка)")
@StringFieldChecker("token", required=True, desc="Входной параметр: токен доступа (обязательная строка)")
class BulkYouTrackIssueToCsvAction(BaseSimpleAction):
    """
    Оркестрирующее действие: загружает задачи из YouTrack и сохраняет в CSV-файлы.
    Параметры:
        base_url, token, page_size, project_id (опц.), user_stories_file (опц.), tasks_file (опц.)
    """

    @InstanceOfChecker("managers", expected_class=list, desc="Результат _preHandleAspect: список менеджеров соединений")
    @InstanceOfChecker("savers", expected_class=list, desc="Результат _preHandleAspect: список кортежей (context, saver, card_types)")
    def _preHandleAspect(self, ctx: Context, params: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """Создаёт менеджеры соединений и saver'ы на основе переданных файлов."""
        managers = []
        savers: List[Tuple[TransactionContext, object, List[str]]] = []

        csv_saver = YouTrackIssuesCSVSaver()

        user_stories_file = params.get("user_stories_file")
        if user_stories_file:
            mgr = CsvConnectionManager(filepath=user_stories_file)
            mgr.open()
            managers.append(mgr)
            tx_ctx = TransactionContext(base_ctx=ctx, connection=mgr)
            savers.append((
                tx_ctx,
                csv_saver,
                ["Пользовательская история", "Техническая история"]
            ))

        tasks_file = params.get("tasks_file")
        if tasks_file:
            mgr = CsvConnectionManager(filepath=tasks_file)
            mgr.open()
            managers.append(mgr)
            tx_ctx = TransactionContext(base_ctx=ctx, connection=mgr)
            savers.append((
                tx_ctx,
                csv_saver,
                [
                    "Разработка",
                    "Аналитика и проектирование",
                    "Решение инцидентов",
                    "Работа вместо системы"
                ]
            ))

        if not savers:
            raise ValueError("Не указано ни одного файла для сохранения")

        return {"managers": managers, "savers": savers}

    @IntFieldChecker("total_issues", min_value=0, desc="Результат _handleAspect: общее количество загруженных задач")
    @IntFieldChecker("pages", min_value=0, desc="Результат _handleAspect: количество обработанных страниц")
    def _handleAspect(self, ctx: Context, params: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """Запускает загрузчик задач."""
        fetcher = FetchIssuesFromYouTrackAction()
        fetcher_ctx = Context(user_id=ctx.user_id, roles=ctx.roles)

        fetch_params = {
            "base_url": params["base_url"],
            "token": params["token"],
            "page_size": params["page_size"],
            "project_id": params.get("project_id"),
            "savers": result["savers"],
        }

        return fetcher.run(fetcher_ctx, fetch_params)

    @IntFieldChecker("total_issues", min_value=0, desc="Результат _postHandleAspect: общее количество загруженных задач")
    @IntFieldChecker("pages", min_value=0, desc="Результат _postHandleAspect: количество обработанных страниц")
    def _postHandleAspect(self, ctx: Context, params: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """Фиксирует транзакции и возвращает только статистику загрузки."""
        for mgr in result.get("managers", []):
            mgr.commit()
        # Удаляем служебные ключи
        result.pop("managers", None)
        result.pop("savers", None)
        return result
    
    def _onErrorAspect(self, ctx: Context, params: Dict[str, Any], result: Dict[str, Any], error: Exception) -> None:
        """При ошибке откатывает все открытые CSV-соединения."""
        for mgr in result.get("managers", []):
            mgr.rollback()
        logger.error(f"Ошибка в BulkYouTrackIssueToCsvAction: {error}")