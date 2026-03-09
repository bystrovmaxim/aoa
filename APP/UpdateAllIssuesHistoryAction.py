# APP/UpdateAllIssuesHistoryAction.py
import logging
import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from collections import defaultdict

from ActionEngine import (
    BaseSimpleAction,
    Context,
    TransactionContext,
    CheckRoles,
    IntFieldChecker,
    InstanceOfChecker,
    StringFieldChecker,
    PostgresConnectionManager,
    HandleException
)

from .FindIssuesNeedingHistoryUpdateAction import FindIssuesNeedingHistoryUpdateAction
from .FetchIssueStatusHistoryAction import FetchIssueStatusHistoryAction

logger = logging.getLogger(__name__)


@CheckRoles(CheckRoles.ANY, desc="Доступно аутентифицированным пользователям")
@StringFieldChecker("base_url", required=True, desc="URL YouTrack")
@StringFieldChecker("token", required=True, desc="Токен доступа")
@IntFieldChecker("page_size", required=True, min_value=1, max_value=10000, desc="Размер страницы")
@InstanceOfChecker("project_code", expected_class=(str, list), required=False, desc="Код проекта или список кодов (опционально)")
@StringFieldChecker("default_start_date", required=False, not_empty=True, desc="Дата начала по умолчанию (YYYY-MM-DD)")
@StringFieldChecker("pg_host", required=True, desc="Хост PostgreSQL")
@IntFieldChecker("pg_port", required=True, desc="Порт PostgreSQL")
@StringFieldChecker("pg_db", required=True, desc="Имя БД")
@StringFieldChecker("pg_user", required=True, desc="Пользователь PostgreSQL")
@StringFieldChecker("pg_password", required=True, desc="Пароль PostgreSQL")
class UpdateAllIssuesHistoryAction(BaseSimpleAction):
    """
    Обновляет историю статусов для задач по проектам.
    Каждый проект обрабатывается в отдельной транзакции.
    Если проект успешен – транзакция фиксируется, если возникла ошибка – откатывается.
    """

    @InstanceOfChecker("managers", expected_class=list, desc="Внутреннее")
    @InstanceOfChecker("tx_ctx", expected_class=TransactionContext, desc="Внутреннее")
    def _preHandleAspect(self, ctx: Context, params: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        db_params = {
            "host": params["pg_host"],
            "port": params["pg_port"],
            "dbname": params["pg_db"],
            "user": params["pg_user"],
            "password": params["pg_password"],
        }
        logger.debug("Открытие соединения с PostgreSQL")
        mgr = PostgresConnectionManager(db_params)
        mgr.open()
        tx_ctx = TransactionContext(
            user=ctx.user,
            request=ctx.request,
            environment=ctx.environment,
            connection=mgr.connection
        )
        return {"managers": [mgr], "tx_ctx": tx_ctx}

    def _get_project_last_timestamp(self, cur, project_code: str, default_start_date: Optional[str]) -> datetime:
        """Возвращает максимальный timestamp для проекта или дату по умолчанию."""
        cur.execute("""
            SELECT MAX(h.timestamp)
            FROM youtrack.issues_status_history h
            JOIN youtrack.issues i ON h.issue_id = i.id
            WHERE i.project_code = %s
        """, (project_code,))
        row = cur.fetchone()
        if row and row[0]:
            return row[0]
        if default_start_date:
            try:
                return datetime.strptime(default_start_date, "%Y-%m-%d")
            except ValueError:
                logger.warning(f"Неверный default_start_date: {default_start_date}, используем 2000-01-01")
        logger.info(f"История для проекта {project_code} пуста, используем дату 2000-01-01")
        return datetime(2000, 1, 1)

    def _get_all_project_codes(self, cur) -> List[str]:
        cur.execute("SELECT DISTINCT project_code FROM youtrack.issues WHERE project_code IS NOT NULL")
        return [row[0] for row in cur.fetchall()]

    def _add_initial_status_if_needed(self, events: List[Dict], issue_id: str, created: Optional[datetime]) -> List[Dict]:
        INITIAL_STATUS = "Ожидание"
        if any(e["new_status"] == INITIAL_STATUS for e in events):
            return events
        if events:
            first = events[0]
            emulated = {
                "issue_id": issue_id,
                "timestamp": first["timestamp"],
                "author_login": first["author_login"],
                "old_status": None,
                "new_status": INITIAL_STATUS,
            }
            events.insert(0, emulated)
            logger.info(f"Добавлено эмул. '{INITIAL_STATUS}' для {issue_id} на основе первого события")
            return events
        # Нет событий – эмулируем по времени создания или текущему
        if created is None:
            created = datetime.utcnow()
        emulated = {
            "issue_id": issue_id,
            "timestamp": created,
            "author_login": None,
            "old_status": None,
            "new_status": INITIAL_STATUS,
        }
        events.append(emulated)
        logger.info(f"Добавлено эмул. '{INITIAL_STATUS}' для {issue_id} по времени создания")
        return events

    @IntFieldChecker("total_projects_processed", min_value=0)
    @IntFieldChecker("total_issues_processed", min_value=0)
    @IntFieldChecker("total_events_inserted", min_value=0)
    @IntFieldChecker("total_issues_skipped", min_value=0)
    @InstanceOfChecker("details_by_project", expected_class=dict)
    def _handleAspect(self, ctx: Context, params: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        tx_ctx = result["tx_ctx"]
        conn = tx_ctx.connection
        cur = conn.cursor()

        default_start_date = params.get("default_start_date")
        project_param = params.get("project_code")

        # Определяем список проектов для обработки
        if project_param is None:
            projects = self._get_all_project_codes(cur)
        elif isinstance(project_param, str):
            projects = [project_param]
        elif isinstance(project_param, list):
            projects = project_param
        else:
            raise TypeError("project_code должен быть строкой, списком или None")

        if not projects:
            logger.info("Нет проектов для обработки.")
            return {
                "total_projects_processed": 0,
                "total_issues_processed": 0,
                "total_events_inserted": 0,
                "total_issues_skipped": 0,
                "details_by_project": {}
            }

        find_action = FindIssuesNeedingHistoryUpdateAction()
        fetch_action = FetchIssueStatusHistoryAction()

        total_projects = 0
        total_issues_processed = 0
        total_events_inserted = 0
        total_issues_skipped = 0
        details_by_project = {}

        for proj_code in projects:
            logger.info(f"Обработка проекта {proj_code}...")
            project_success = False
            project_processed = 0
            project_events = 0
            project_skipped = 0

            try:
                # Получаем последнюю дату для проекта
                last_global = self._get_project_last_timestamp(cur, proj_code, default_start_date)

                # Получаем список задач проекта из YouTrack
                find_params = {
                    "base_url": params["base_url"],
                    "token": params["token"],
                    "page_size": params["page_size"],
                    "since_timestamp_ms": int(last_global.timestamp() * 1000),
                    "project_code": proj_code,
                }
                find_result = find_action.run(ctx, find_params)
                issues = find_result.get("issues", [])  # список [{"id": "..."}]

                if not issues:
                    logger.info(f"Для проекта {proj_code} нет задач для обновления")
                    # Всё равно закоммитим, чтобы начать новую транзакцию (ничего не меняли)
                    conn.commit()
                    details_by_project[proj_code] = {
                        "issues_processed": 0,
                        "events_inserted": 0,
                        "issues_skipped": 0
                    }
                    total_projects += 1
                    continue

                # Проверяем наличие задач в issues (получаем id и created)
                issue_ids = [issue["id"] for issue in issues]
                placeholders = ','.join(['%s'] * len(issue_ids))
                cur.execute(f"SELECT id, created FROM youtrack.issues WHERE id IN ({placeholders})", issue_ids)
                existing = {row[0]: row[1] for row in cur.fetchall()}

                # Проходим по задачам
                for idx, issue in enumerate(issues, 1):
                    if issue["id"] not in existing:
                        logger.warning(f"Задача {issue['id']} отсутствует в issues. Пропускаем.")
                        project_skipped += 1
                        continue

                    start_time = time.time()
                    from_ms = int(last_global.timestamp() * 1000)

                    fetch_params = {
                        "base_url": params["base_url"],
                        "token": params["token"],
                        "issue_id": issue["id"],
                        "from_timestamp_ms": from_ms
                    }

                    # Savepoint для задачи
                    sp_task = f"sp_{proj_code}_{idx}"
                    cur.execute(f"SAVEPOINT {sp_task}")

                    try:
                        fetch_result = fetch_action.run(ctx, fetch_params)
                        events = fetch_result.get("events", [])

                        if not events and from_ms == 0:
                            # Первая загрузка – пробуем эмуляцию
                            created = existing[issue["id"]]
                            events = self._add_initial_status_if_needed(events, issue["id"], created)

                        if not events:
                            cur.execute(f"RELEASE SAVEPOINT {sp_task}")
                            continue

                        # Вставляем события
                        inserted = 0
                        for event in events:
                            cur.execute(
                                """
                                INSERT INTO youtrack.issues_status_history
                                    (issue_id, timestamp, author_login, old_status, new_status)
                                VALUES (%s, %s, %s, %s, %s)
                                ON CONFLICT (issue_id, timestamp) DO NOTHING
                                """,
                                (event["issue_id"], event["timestamp"], event["author_login"],
                                 event["old_status"], event["new_status"])
                            )
                            if cur.rowcount > 0:
                                inserted += 1

                        project_events += inserted
                        project_processed += 1
                        elapsed = time.time() - start_time
                        print(f"✅ [{proj_code} {idx}/{len(issues)}] {issue['id']}: вставлено {inserted} событий ({elapsed:.1f}с)")

                        cur.execute(f"RELEASE SAVEPOINT {sp_task}")

                    except Exception as e:
                        cur.execute(f"ROLLBACK TO SAVEPOINT {sp_task}")
                        print(f"❌ [{proj_code} {idx}/{len(issues)}] {issue['id']}: ошибка - {e}")
                        logger.error(f"Ошибка при обработке задачи {issue['id']} проекта {proj_code}: {e}")
                        # Продолжаем со следующей задачей (проект не прерывается)

                # Проект успешно обработан – фиксируем транзакцию
                conn.commit()
                project_success = True
                logger.info(f"Проект {proj_code} успешно обработан, транзакция зафиксирована.")

            except Exception as e:
                # Ошибка на уровне проекта (например, при получении списка задач)
                conn.rollback()
                logger.error(f"Ошибка при обработке проекта {proj_code}: {e}")
                details_by_project[proj_code] = {
                    "error": str(e),
                    "issues_processed": 0,
                    "events_inserted": 0,
                    "issues_skipped": 0
                }
                total_projects += 1
                continue

            if project_success:
                details_by_project[proj_code] = {
                    "issues_processed": project_processed,
                    "events_inserted": project_events,
                    "issues_skipped": project_skipped
                }
                total_projects += 1
                total_issues_processed += project_processed
                total_events_inserted += project_events
                total_issues_skipped += project_skipped

        return {
            "total_projects_processed": total_projects,
            "total_issues_processed": total_issues_processed,
            "total_events_inserted": total_events_inserted,
            "total_issues_skipped": total_issues_skipped,
            "details_by_project": details_by_project
        }

    @IntFieldChecker("total_projects_processed", min_value=0)
    @IntFieldChecker("total_issues_processed", min_value=0)
    @IntFieldChecker("total_events_inserted", min_value=0)
    @IntFieldChecker("total_issues_skipped", min_value=0)
    @InstanceOfChecker("details_by_project", expected_class=dict)
    def _postHandleAspect(self, ctx: Context, params: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        # В _handleAspect мы уже коммитили каждый проект, но после цикла транзакция может быть открыта?
        # Если последний проект не вызвал commit (например, из-за ошибки), то нужно откатить.
        # Проще в конце выполнить commit, но если все проекты уже закоммичены, лишний commit не повредит.
        for mgr in result.get("managers", []):
            try:
                mgr.commit()
            except Exception:
                mgr.rollback()
        result.pop("managers", None)
        result.pop("tx_ctx", None)
        return result

    def _onErrorAspect(self, ctx: Context, params: Dict[str, Any], result: Dict[str, Any], error: Exception) -> None:
        logger.error(f"Ошибка в UpdateAllIssuesHistoryAction: {error}")
        for mgr in result.get("managers", []):
            try:
                mgr.rollback()
            except Exception:
                pass