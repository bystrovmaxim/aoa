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
from .FetchIssuesToCsvAction import FetchIssuesToCsvAction

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