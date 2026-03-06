# API/YouTrackAPI.py (фрагмент с инициализацией координатора)
"""
FastAPI-приложение для доступа к функциям YouTrack через ActionEngine.
Все защищённые эндпоинты требуют валидного API-ключа в заголовке X-API-Key.
"""

import logging

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Depends, HTTPException, Request
from pydantic import BaseModel
from datetime import date
from typing import Optional, List

from EntryPoint.YouTrackEntryPoint import YouTrackEntryPoint
from ActionEngine import Context

# Новые компоненты аутентификации
from API.HTTPContextAssembler import HTTPContextAssembler
from API.ExtractorCredentialsHTTP import ExtractorCredentialsHTTP   # переименованный файл
from EntryPoint.Auth.EnvApiKeyAuthenticator import EnvApiKeyAuthenticator
from ActionEngine.Auth.AuthCoordinator import AuthCoordinator

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("youtrack-api")

# --- Инициализация компонентов аутентификации ---

# Экстрактор API-ключа из заголовка X-API-Key
extractor = ExtractorCredentialsHTTP(header_name="X-API-Key")

# Аутентификатор на основе переменных окружения
authenticator = EnvApiKeyAuthenticator()

# Сборщик метаданных HTTP-запроса
assembler = HTTPContextAssembler()

# Координатор, объединяющий все стратегии
coordinator = AuthCoordinator(
    extractor=extractor,
    authenticator=authenticator,
    assembler=assembler
)

# --- Зависимость для получения контекста ---
async def get_current_context(request: Request) -> Context:
    """
    Зависимость FastAPI, использующая координатор для аутентификации и создания контекста.
    Если аутентификация не удалась (нет ключа или он недействителен), выбрасывает HTTP 401.
    """
    ctx = coordinator.process(request)
    if ctx is None:
        raise HTTPException(status_code=401, detail="Authentication failed")
    return ctx


# --- Pydantic модели запросов и ответов ---

class CsvRequest(BaseModel):
    """Модель запроса для выгрузки в CSV."""
    user_stories_file: Optional[str] = None
    tasks_file: Optional[str] = None
    page_size: int = 100
    project_id: Optional[str] = None


class PostgresRequest(BaseModel):
    """Модель запроса для выгрузки в PostgreSQL."""
    project_id: Optional[str] = None
    page_size: int = 100
    snapshot_date: Optional[date] = None


class DeleteSnapshotRequest(BaseModel):
    """Модель запроса для удаления снимка."""
    snapshot_date: date
    tables: List[str]
    schema: str = "youtrack"


class StandardResponse(BaseModel):
    """Стандартный формат ответа для всех операций."""
    success: bool
    result: Optional[dict] = None
    errors: List[str] = []


# --- Создаём приложение FastAPI ---
app = FastAPI(
    title="YouTrack Gateway API",
    description="HTTP API для операций с YouTrack (требуется API-ключ)",
    version="1.0.0"
)


# --- Эндпоинты ---

@app.post("/init_database", response_model=StandardResponse)
async def init_database(
    ctx: Context = Depends(get_current_context)
) -> StandardResponse:
    """
    Инициализирует таблицы в PostgreSQL.
    Требуется API-ключ с правами администратора.
    """
    logger.info(f"init_database called by user: {ctx.user.user_id}")
    result = YouTrackEntryPoint.init_database(ctx)
    return StandardResponse(**result)


@app.post("/bulk_youtrack_issue_to_csv", response_model=StandardResponse)
async def bulk_csv(
    request: CsvRequest,
    ctx: Context = Depends(get_current_context)
) -> StandardResponse:
    """
    Загружает задачи из YouTrack и сохраняет в CSV-файлы.
    - user_stories_file: путь для сохранения историй
    - tasks_file: путь для сохранения задач
    - page_size: размер страницы (1-5000)
    - project_id: опциональный фильтр по проекту
    """
    logger.info(f"bulk_csv called by user: {ctx.user.user_id}")
    result = YouTrackEntryPoint.bulk_youtrack_issue_to_csv(
        ctx=ctx,
        user_stories_file=request.user_stories_file,
        tasks_file=request.tasks_file,
        page_size=request.page_size,
        project_id=request.project_id
    )
    return StandardResponse(**result)


@app.post("/bulk_youtrack_issue_to_postgres", response_model=StandardResponse)
async def bulk_postgres(
    request: PostgresRequest,
    ctx: Context = Depends(get_current_context)
) -> StandardResponse:
    """
    Загружает снимки задач в PostgreSQL.
    - project_id: опциональный фильтр по проекту
    - page_size: размер страницы (1-5000)
    - snapshot_date: дата снимка (YYYY-MM-DD), если не указана – сегодня
    """
    logger.info(f"bulk_postgres called by user: {ctx.user.user_id}")
    result = YouTrackEntryPoint.bulk_youtrack_issue_to_postgres(
        ctx=ctx,
        project_id=request.project_id,
        page_size=request.page_size,
        snapshot_date=request.snapshot_date
    )
    return StandardResponse(**result)


@app.post("/delete_snapshot", response_model=StandardResponse)
async def delete_snapshot(
    request: DeleteSnapshotRequest,
    ctx: Context = Depends(get_current_context)
) -> StandardResponse:
    """
    Удаляет все записи за указанную дату из заданных таблиц.
    - snapshot_date: дата снимка для удаления
    - tables: список таблиц (например, ['user_tech_stories', 'taskitems'])
    - schema: схема БД (по умолчанию 'youtrack')
    """
    logger.info(f"delete_snapshot called by user: {ctx.user.user_id}")
    result = YouTrackEntryPoint.delete_snapshot(
        ctx=ctx,
        snapshot_date=request.snapshot_date,
        tables=request.tables,
        schema=request.schema
    )
    return StandardResponse(**result)


@app.get("/health", response_model=dict)
async def health():
    """Проверка работоспособности сервиса (не требует аутентификации)."""
    return {"status": "ok"}