# Файл: YouTrackMCP/YouTrackMCPServer.py
"""
Фасад для вызова действий YouTrack.

Требования:
- Документирование всех классов.
- Документирование всех методов.
- Текст исколючений писать на русском.
"""
import logging
from typing import Optional, Dict, Any

from ActionEngine.Context import Context
from ActionEngine.TransactionContext import TransactionContext
from ActionEngine.CsvConnectionManager import CsvConnectionManager
from .FetchIssuesFromYouTrackAction import FetchIssuesFromYouTrackAction
from .UserTechStoryIssuesCSVSaver import UserTechStoryIssuesCSVSaver

logger = logging.getLogger(__name__)


class YouTrackMCPServer:
    """
    Фасад для вызова действий (сообщений) YouTrack.

    Каждое бизнес-действие представлено отдельным статическим методом.
    Методы принимают все необходимые параметры в явном виде, а также контекст выполнения.
    Внутри метода создаётся экземпляр соответствующего действия, вызывается его метод run,
    и результат возвращается в едином формате: словарь с полями success, result, errors.
    Все исключения перехватываются, логируются и преобразуются в стандартный ответ с ошибкой.
    """

    @staticmethod
    def fetch_issues_to_csv(
        ctx: Context,
        base_url: str,
        token: str,
        output_file: str,
        page_size: int,
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Загружает задачи из YouTrack и сохраняет их в CSV-файл.

        Если указан project_id, загружаются задачи только указанного проекта,
        иначе — все задачи, доступные по токену (может быть очень много).

        Параметры:
            ctx (Context): контекст выполнения (содержит информацию о пользователе и его ролях).
            base_url (str): базовый URL экземпляра YouTrack (например, https://youtrack.brusnika.tech).
            token (str): перманентный токен доступа к YouTrack.
            output_file (str): полный путь к файлу, в который будет сохранён CSV.
            page_size (int): количество задач на одной странице (от 1 до 500).
            project_id (Optional[str]): идентификатор проекта (например, "OPD_IPPM").
                Если не указан, выгружаются задачи из всех проектов, доступных по токену.

        Возвращает:
            Dict[str, Any] – словарь с ключами:
                success (bool): True, если операция выполнена без ошибок.
                result (Any): результат действия (словарь с количеством задач и путём к файлу).
                errors (List[str]): список сообщений об ошибках (пуст при успехе).
        """
        # Формируем параметры для действия
        params = {
            "base_url": base_url,
            "token": token,
            "output_file": output_file,
            "page_size": page_size,
        }
        if project_id is not None:
            params["project_id"] = project_id

        # Создаём экземпляр действия
        action = FetchIssuesToCsvAction()

        try:
            result = action.run(ctx, params)
            return {"success": True, "result": result, "errors": []}
        except Exception as e:
            # Любое исключение (включая наши бизнес-исключения) логируем и возвращаем как ошибку.
            # Это гарантирует, что внешний клиент (например, n8n) всегда получит структурированный ответ.
            logger.exception("Ошибка в FetchIssuesToCsvAction")
            return {"success": False, "result": None, "errors": [str(e)]}
        
    
    # Файл: YouTrackMCP/YouTrackMCPServer.py (фрагмент)

    @staticmethod
    def fetch_user_stories_to_csv(
        base_url: str,
        token: str,
        output_file: str,
        page_size: int = 100,
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Загружает из YouTrack все задачи типов "Пользовательская история" и "Техническая история"
        и сохраняет их в CSV-файл.
        """
        # 1. Создаём менеджер соединения для CSV и открываем транзакцию
        mgr = CsvConnectionManager(filepath=output_file)
        mgr.open()

        # 2. Создаём транзакционный контекст с соединением (одной строкой)
        tx_ctx = TransactionContext(base_ctx=Context(user_id="system", roles=["user"]), connection=mgr)

        # 3. Создаём экземпляр saver'а
        saver = UserTechStoryIssuesCSVSaver()

        # 4. Создаём действие-загрузчик
        fetcher = FetchIssuesFromYouTrackAction()

        # 5. Формируем параметры: список кортежей (контекст, сейвер)
        params = {
            "base_url": base_url,
            "token": token,
            "page_size": page_size,
            "project_id": project_id,
            "savers": [(tx_ctx, saver)],   # один сейвер с его контекстом
        }

        try:
            result = fetcher.run(tx_ctx, params)   # контекст самого загрузчика (tx_ctx) может не использоваться, но передаём для совместимости
            mgr.commit()
            return {"success": True, "result": result, "errors": []}
        except Exception as e:
            mgr.rollback()
            logger.exception("Ошибка в fetch_user_stories_to_csv")
            return {"success": False, "result": None, "errors": [str(e)]}