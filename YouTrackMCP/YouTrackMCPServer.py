# Файл: YouTrackMCP/YouTrackMCPServer.py
import logging
import os
from typing import Optional, Dict, Any

from ActionEngine.Context import Context
from ActionEngine.TransactionContext import TransactionContext
from ActionEngine.CsvConnectionManager import CsvConnectionManager
from .FetchIssuesFromYouTrackAction import FetchIssuesFromYouTrackAction
from .YouTrackIssuesCSVSaver import YouTrackIssuesCSVSaver

logger = logging.getLogger(__name__)


class YouTrackMCPServer:
    """
    Фасад для вызова действий (сообщений) YouTrack.
    """

    @staticmethod
    def bulk_youtrack_issue_to_csv(
        user_stories_file: Optional[str] = None,
        tasks_file: Optional[str] = None,
        page_size: int = 100,
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Загружает задачи из YouTrack и раскладывает их по разным CSV-файлам в зависимости от типа.

        Параметры подключения читаются из переменных окружения:
            YOUTRACK_URL (обязательна)
            YOUTRACK_TOKEN (обязательна)

        Параметры:
            user_stories_file: путь к CSV-файлу для пользовательских и технических историй.
            tasks_file: путь к CSV-файлу для задач (разработка, аналитика, решение инцидентов, работа вместо системы).
            page_size: количество задач на странице (1-500).
            project_id: идентификатор проекта (например, "OPD_IPPM").

        Возвращает словарь с ключами success, result, errors.
        """
        # Чтение параметров из окружения
        base_url = os.getenv("YOUTRACK_URL")
        if base_url is None:
            return {"success": False, "result": None, "errors": ["Переменная окружения YOUTRACK_URL не задана"]}

        token = os.getenv("YOUTRACK_TOKEN")
        if token is None:
            return {"success": False, "result": None, "errors": ["Переменная окружения YOUTRACK_TOKEN не задана"]}

        savers = []      # список кортежей (context, saver)
        managers = []    # для закрытия соединений

        # Сейвер для историй
        if user_stories_file:
            mgr = CsvConnectionManager(filepath=user_stories_file)
            mgr.open()
            managers.append(mgr)
            tx_ctx = TransactionContext(
                base_ctx=Context(user_id="system", roles=["user"]),
                connection=mgr
            )
            saver = YouTrackIssuesCSVSaver(
                strategy=["Пользовательская история", "Техническая история"]
            )
            savers.append((tx_ctx, saver))

        # Сейвер для задач
        if tasks_file:
            mgr = CsvConnectionManager(filepath=tasks_file)
            mgr.open()
            managers.append(mgr)
            tx_ctx = TransactionContext(
                base_ctx=Context(user_id="system", roles=["user"]),
                connection=mgr
            )
            saver = YouTrackIssuesCSVSaver(
                strategy=[
                    "Разработка",
                    "Аналитика и проектирование",
                    "Решение инцидентов",
                    "Работа вместо системы"
                ]
            )
            savers.append((tx_ctx, saver))

        if not savers:
            return {"success": False, "result": None, "errors": ["Не указано ни одного файла для сохранения"]}

        # Действие-загрузчик
        fetcher = FetchIssuesFromYouTrackAction()
        params = {
            "base_url": base_url,
            "token": token,
            "page_size": page_size,
            "project_id": project_id,
            "savers": savers,
        }

        main_ctx = savers[0][0] if savers else None

        try:
            result = fetcher.run(main_ctx, params)
            for mgr in managers:
                mgr.commit()
            return {"success": True, "result": result, "errors": []}
        except Exception as e:
            for mgr in managers:
                mgr.rollback()
            logger.exception("Ошибка в bulk_youtrack_issue_to_csv")
            return {"success": False, "result": None, "errors": [str(e)]}