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
from .TaskItemsIssuesCSVSaver import TaskItemsIssuesCSVSaver

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

    @staticmethod
    def bulk_youtrack_issue_to_csv(
        base_url: str,
        token: str,
        user_stories_file: Optional[str] = None,
        tasks_file: Optional[str] = None,
        page_size: int = 100,
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Загружает задачи из YouTrack и раскладывает их по разным CSV-файлам в зависимости от типа.

        Параметры:
            base_url (str): базовый URL экземпляра YouTrack.
            token (str): перманентный токен доступа к YouTrack.
            user_stories_file (Optional[str]): путь к CSV-файлу для сохранения пользовательских и технических историй.
                Если None, этот тип не сохраняется.
            tasks_file (Optional[str]): путь к CSV-файлу для сохранения задач (типы "Разработка" и "Аналитика и проектирование").
                Если None, этот тип не сохраняется.
            page_size (int): количество задач на одной странице (от 1 до 500).
            project_id (Optional[str]): идентификатор проекта (например, "OPD_IPPM").

        Возвращает:
            Dict[str, Any] – словарь с ключами:
                success (bool): True, если операция выполнена без ошибок.
                result (Any): результат действия (словарь с количеством задач и путём к файлу).
                errors (List[str]): список сообщений об ошибках (пуст при успехе).
        """
        # Список кортежей (контекст, сейвер)
        savers = []
        managers = []  # чтобы потом закрыть все

        # Если указан файл для пользовательских историй
        if user_stories_file:
            mgr = CsvConnectionManager(filepath=user_stories_file)
            mgr.open()
            managers.append(mgr)
            tx_ctx = TransactionContext(base_ctx=Context(user_id="system", roles=["user"]), connection=mgr)
            saver = UserTechStoryIssuesCSVSaver()
            savers.append((tx_ctx, saver))

        # Если указан файл для задач
        if tasks_file:
            mgr = CsvConnectionManager(filepath=tasks_file)
            mgr.open()
            managers.append(mgr)
            tx_ctx = TransactionContext(base_ctx=Context(user_id="system", roles=["user"]), connection=mgr)
            saver = TaskItemsIssuesCSVSaver()
            savers.append((tx_ctx, saver))

        if not savers:
            return {"success": False, "result": None, "errors": ["Не указано ни одного файла для сохранения"]}

        # Создаём действие-загрузчик
        fetcher = FetchIssuesFromYouTrackAction()

        params = {
            "base_url": base_url,
            "token": token,
            "page_size": page_size,
            "project_id": project_id,
            "savers": savers,
        }

        # Контекст для самого загрузчика (не используется, но передаём первый попавшийся)
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