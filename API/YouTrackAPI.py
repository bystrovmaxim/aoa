# API/YouTrackAPI.py
import os
import logging
from typing import Optional, List
from datetime import date
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Импортируем фасад из Gateway
from EntryPoint.YouTrackMCPServer import YouTrackMCPServer

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("youtrack-api")

app = FastAPI(title="YouTrack Gateway API", description="HTTP API для операций с YouTrack")

# --- Pydantic модели запросов и ответов ---

class CsvRequest(BaseModel):
    user_stories_file: Optional[str] = None
    tasks_file: Optional[str] = None
    page_size: int = 100
    project_id: Optional[str] = None

class PostgresRequest(BaseModel):
    project_id: Optional[str] = None
    page_size: int = 100
    snapshot_date: Optional[date] = None

class DeleteSnapshotRequest(BaseModel):
    snapshot_date: date
    tables: List[str]
    schema: str = "youtrack"

class StandardResponse(BaseModel):
    success: bool
    result: Optional[dict]
    errors: List[str]

# --- Эндпоинты ---

@app.post("/init_database", response_model=StandardResponse)
def init_database():
    """Инициализирует таблицы в PostgreSQL."""
    result = YouTrackMCPServer.init_database()
    return result

@app.post("/bulk_youtrack_issue_to_csv", response_model=StandardResponse)
def bulk_csv(request: CsvRequest):
    """Загружает задачи из YouTrack и сохраняет в CSV-файлы."""
    result = YouTrackMCPServer.bulk_youtrack_issue_to_csv(
        user_stories_file=request.user_stories_file,
        tasks_file=request.tasks_file,
        page_size=request.page_size,
        project_id=request.project_id
    )
    return result

@app.post("/bulk_youtrack_issue_to_postgres", response_model=StandardResponse)
def bulk_postgres(request: PostgresRequest):
    """Загружает снимки задач в PostgreSQL."""
    result = YouTrackMCPServer.bulk_youtrack_issue_to_postgres(
        project_id=request.project_id,
        page_size=request.page_size,
        snapshot_date=request.snapshot_date
    )
    return result

@app.post("/delete_snapshot", response_model=StandardResponse)
def delete_snapshot(request: DeleteSnapshotRequest):
    """Удаляет все записи за указанную дату из заданных таблиц."""
    result = YouTrackMCPServer.delete_snapshot(
        snapshot_date=request.snapshot_date,
        tables=request.tables,
        schema=request.schema
    )
    return result

@app.get("/health")
def health():
    return {"status": "ok"}

# Для запуска: uvicorn API.YouTrackAPI:app --host 0.0.0.0 --port 8000