# EntryPoint/YouTrackEntryPoint.py
"""
Тонкий фасад (точка входа) для всех оркестрирующих действий.
Все публичные методы первым параметром принимают объект Context,
содержащий информацию о пользователе, запросе и окружении.

Контекст передаётся из внешних слоёв (FastAPI, MCP) после успешной аутентификации.
Это гарантирует, что фасад не занимается аутентификацией, а только вызывает бизнес-действия.
"""

import os
import logging
from typing import Optional, Dict, Any
from datetime import date
from typing import List

from ActionEngine import (
    Context,
    TransactionContext,
    PostgresConnectionManager,
    UserInfo)

from .BulkYouTrackIssueToCsvAction import BulkYouTrackIssueToCsvAction
from .BulkYouTrackIssueToPostgresAction import BulkYouTrackIssueToPostgresAction
from .InitDatabaseServerAction import InitDatabaseServerAction
from .DeleteSnapshotServerAction import DeleteSnapshotServerAction

logger = logging.getLogger(__name__)


class YouTrackEntryPoint:
    """
    Тонкий фасад для вызова оркестрирующих действий из внешних систем (n8n, FastAPI, MCP).

    Все методы принимают контекст первым параметром, что позволяет
    передавать информацию об аутентифицированном пользователе и метаданные запроса.
    Фасад не занимается созданием контекста – он только использует готовый.
    """

    @staticmethod
    def init_database(ctx: Context) -> Dict[str, Any]:
        """
        Инициализирует таблицы в PostgreSQL.

        Читает параметры подключения из переменных окружения:
            POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD.

        :param ctx: контекст выполнения (содержит информацию о пользователе)
        :return: словарь с результатом (стандартный ответ)
        """
        # --- Чтение параметров подключения ---
        pg_host = os.getenv("POSTGRES_HOST")
        if not pg_host:
            return {"success": False, "result": None, "errors": ["POSTGRES_HOST не задан"]}
        try:
            pg_port = int(os.getenv("POSTGRES_PORT", "5432"))
        except ValueError:
            return {"success": False, "result": None, "errors": ["POSTGRES_PORT должен быть числом"]}
        pg_db = os.getenv("POSTGRES_DB")
        pg_user = os.getenv("POSTGRES_USER")
        pg_password = os.getenv("POSTGRES_PASSWORD")
        if not pg_db or not pg_user or not pg_password:
            return {"success": False, "result": None, "errors": ["POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD должны быть заданы"]}

        db_params = {
            "host": pg_host,
            "port": pg_port,
            "dbname": pg_db,
            "user": pg_user,
            "password": pg_password,
        }

        # --- Создание менеджера соединения ---
        mgr = PostgresConnectionManager(db_params)
        mgr.open()

        # --- Создание транзакционного контекста ---
        # Копируем пользователя и окружение из переданного ctx, добавляем соединение
        tx_ctx = TransactionContext(
            user=ctx.user,
            request=ctx.request,
            environment=ctx.environment,
            connection=mgr.connection
        )

        action = InitDatabaseServerAction()
        try:
            result = action.run(tx_ctx, {})
            mgr.commit()
            return {"success": True, "result": result, "errors": []}
        except Exception as e:
            mgr.rollback()
            logger.exception("Ошибка при инициализации БД")
            return {"success": False, "result": None, "errors": [str(e)]}

    @staticmethod
    def bulk_youtrack_issue_to_csv(
        ctx: Context,
        user_stories_file: Optional[str] = None,
        tasks_file: Optional[str] = None,
        page_size: int = 100,
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Загружает задачи из YouTrack и сохраняет в CSV-файлы.

        Читает параметры YouTrack из переменных окружения:
            YOUTRACK_URL, YOUTRACK_TOKEN.

        :param ctx: контекст выполнения
        :param user_stories_file: путь к CSV-файлу для историй (опционально)
        :param tasks_file: путь к CSV-файлу для задач (опционально)
        :param page_size: размер страницы (1-5000)
        :param project_id: идентификатор проекта (опционально)
        :return: стандартный ответ с результатом
        """
        base_url = os.getenv("YOUTRACK_URL")
        token = os.getenv("YOUTRACK_TOKEN")
        if not base_url or not token:
            return {"success": False, "result": None, "errors": ["YOUTRACK_URL или YOUTRACK_TOKEN не заданы"]}

        action = BulkYouTrackIssueToCsvAction()
        params = {
            "base_url": base_url,
            "token": token,
            "user_stories_file": user_stories_file,
            "tasks_file": tasks_file,
            "page_size": page_size,
            "project_id": project_id,
        }
        try:
            result = action.run(ctx, params)
            return {"success": True, "result": result, "errors": []}
        except Exception as e:
            logger.exception("Ошибка в bulk_youtrack_issue_to_csv")
            return {"success": False, "result": None, "errors": [str(e)]}

    @staticmethod
    def bulk_youtrack_issue_to_postgres(
        ctx: Context,
        project_id: Optional[str] = None,
        page_size: int = 100,
        snapshot_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """
        Загружает задачи из YouTrack и сохраняет снимки в PostgreSQL.

        Читает параметры YouTrack из переменных окружения:
            YOUTRACK_URL, YOUTRACK_TOKEN.
        Читает параметры PostgreSQL из переменных окружения:
            POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD.

        :param ctx: контекст выполнения
        :param project_id: идентификатор проекта (опционально)
        :param page_size: размер страницы (1-5000)
        :param snapshot_date: дата снимка (YYYY-MM-DD). Если не указана, используется сегодня.
        :return: стандартный ответ с результатом
        """
        base_url = os.getenv("YOUTRACK_URL")
        token = os.getenv("YOUTRACK_TOKEN")
        if not base_url or not token:
            return {"success": False, "result": None, "errors": ["YOUTRACK_URL или YOUTRACK_TOKEN не заданы"]}

        pg_host = os.getenv("POSTGRES_HOST")
        if not pg_host:
            return {"success": False, "result": None, "errors": ["POSTGRES_HOST не задан"]}
        try:
            pg_port = int(os.getenv("POSTGRES_PORT", "5432"))
        except ValueError:
            return {"success": False, "result": None, "errors": ["POSTGRES_PORT должен быть числом"]}
        pg_db = os.getenv("POSTGRES_DB")
        pg_user = os.getenv("POSTGRES_USER")
        pg_password = os.getenv("POSTGRES_PASSWORD")
        if not pg_db or not pg_user or not pg_password:
            return {"success": False, "result": None, "errors": ["POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD должны быть заданы"]}

        action = BulkYouTrackIssueToPostgresAction()
        params = {
            "base_url": base_url,
            "token": token,
            "project_id": project_id,
            "page_size": page_size,
            "snapshot_date": snapshot_date.isoformat() if snapshot_date else None,
            "pg_host": pg_host,
            "pg_port": pg_port,
            "pg_db": pg_db,
            "pg_user": pg_user,
            "pg_password": pg_password,
        }
        try:
            result = action.run(ctx, params)
            return {"success": True, "result": result, "errors": []}
        except Exception as e:
            logger.exception("Ошибка в bulk_youtrack_issue_to_postgres")
            return {"success": False, "result": None, "errors": [str(e)]}
        
    @staticmethod
    def delete_snapshot(
        ctx: Context,
        snapshot_date: date,
        tables: List[str],
        schema: str = "youtrack"
    ) -> Dict[str, Any]:
        """
        Удаляет все записи за указанную дату из заданных таблиц.

        Параметры подключения PostgreSQL берутся из переменных окружения:
            POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD.

        :param ctx: контекст выполнения
        :param snapshot_date: дата снимка для удаления
        :param tables: список имён таблиц (например, ['user_tech_stories', 'taskitems'])
        :param schema: схема базы данных (по умолчанию 'youtrack')
        :return: стандартный ответ с количеством удалённых записей
        """
        pg_host = os.getenv("POSTGRES_HOST")
        if not pg_host:
            return {"success": False, "result": None, "errors": ["POSTGRES_HOST не задан"]}
        try:
            pg_port = int(os.getenv("POSTGRES_PORT", "5432"))
        except ValueError:
            return {"success": False, "result": None, "errors": ["POSTGRES_PORT должен быть числом"]}
        pg_db = os.getenv("POSTGRES_DB")
        pg_user = os.getenv("POSTGRES_USER")
        pg_password = os.getenv("POSTGRES_PASSWORD")
        if not pg_db or not pg_user or not pg_password:
            return {"success": False, "result": None, "errors": ["POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD должны быть заданы"]}

        action = DeleteSnapshotServerAction()
        params = {
            "snapshot_date": snapshot_date.isoformat(),
            "tables": tables,
            "schema": schema,
            "pg_host": pg_host,
            "pg_port": pg_port,
            "pg_db": pg_db,
            "pg_user": pg_user,
            "pg_password": pg_password,
        }
        try:
            result = action.run(ctx, params)
            return {"success": True, "result": result, "errors": []}
        except Exception as e:
            logger.exception("Ошибка при удалении снимка")
            return {"success": False, "result": None, "errors": [str(e)]}