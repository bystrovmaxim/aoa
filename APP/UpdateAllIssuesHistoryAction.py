import logging
import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

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

from .UpdateSingleIssueHistoryAction import UpdateSingleIssueHistoryAction

logger = logging.getLogger(__name__)

BATCH_SIZE = 1


@CheckRoles(CheckRoles.ANY, desc="Доступно аутентифицированным пользователям")
@StringFieldChecker("base_url", required=True, desc="URL YouTrack")
@StringFieldChecker("token", required=True, desc="Токен доступа")
@StringFieldChecker("project_id", required=False, not_empty=True, desc="Фильтр по проекту (опционально)")
@StringFieldChecker("pg_host", required=True, desc="Хост PostgreSQL")
@IntFieldChecker("pg_port", required=True, desc="Порт PostgreSQL")
@StringFieldChecker("pg_db", required=True, desc="Имя БД")
@StringFieldChecker("pg_user", required=True, desc="Пользователь PostgreSQL")
@StringFieldChecker("pg_password", required=True, desc="Пароль PostgreSQL")
class UpdateAllIssuesHistoryAction(BaseSimpleAction):
    """
    Обновляет историю статусов для всех задач, которые изменились после последней обработки.
    Для каждой задачи определяется имя поля статуса в зависимости от её типа:
        - 'Пользовательская история', 'Техническая история' → '_Статус истории'
        - остальные (задачи) → '_Статус задачи'
    Вызывается UpdateSingleIssueHistoryAction с переданным last_timestamp_ms (максимальный timestamp из истории статусов).
    Коммит происходит пакетами по BATCH_SIZE задач.
    После успешной обработки задачи обновляется поле last_activity_processed = NOW().
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
        mgr = PostgresConnectionManager(db_params)
        mgr.open()
        tx_ctx = TransactionContext(
            user=ctx.user,
            request=ctx.request,
            environment=ctx.environment,
            connection=mgr.connection
        )
        return {"managers": [mgr], "tx_ctx": tx_ctx}

    def _get_issues_to_update(self, cur, project_id: Optional[str]) -> List[Tuple[str, Optional[datetime], str]]:
        """
        Возвращает список кортежей (issue_id, max_timestamp, type_issue) для задач,
        у которых last_update > last_activity_processed (или last_activity_processed IS NULL).
        Если задан project_id, дополнительно фильтрует по project_code.
        """
        query = """
            SELECT
                i.id,
                (SELECT MAX(timestamp) FROM youtrack.issues_status_history WHERE issue_id = i.id) as max_ts,
                i.type_issue
            FROM youtrack.issues i
            WHERE (i.last_activity_processed IS NULL OR i.last_update > i.last_activity_processed)
        """
        params_list = []
        if project_id:
            query += " AND i.project_code = %s"
            params_list.append(project_id)

        cur.execute(query, params_list)
        rows = cur.fetchall()
        return [(row[0], row[1], row[2]) for row in rows]

    @IntFieldChecker("total_issues_processed", min_value=0)
    @IntFieldChecker("total_events_inserted", min_value=0)
    @IntFieldChecker("total_issues_skipped", min_value=0)
    @IntFieldChecker("total_issues_failed", min_value=0)
    @InstanceOfChecker("details", expected_class=dict)
    def _handleAspect(self, ctx: Context, params: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        tx_ctx = result["tx_ctx"]
        conn = tx_ctx.connection
        cur = conn.cursor()

        base_url = params["base_url"]
        token = params["token"]
        project_id = params.get("project_id")

        issues = self._get_issues_to_update(cur, project_id)
        if not issues:
            logger.info("Нет задач для обновления.")
            return {
                "total_issues_processed": 0,
                "total_events_inserted": 0,
                "total_issues_skipped": 0,
                "total_issues_failed": 0,
                "details": {}
            }

        single_action = UpdateSingleIssueHistoryAction()
        # Создаём простой контекст для вызова UpdateSingleIssueHistoryAction (не транзакционный, так как он сам использует переданный tx_ctx)
        # Но UpdateSingleIssueHistoryAction требует TransactionContext, мы передадим tx_ctx напрямую.

        total_processed = 0
        total_inserted = 0
        total_skipped = 0
        total_failed = 0
        batch_counter = 0
        details = {}

        for idx, (issue_id, max_ts, issue_type) in enumerate(issues, 1):
            # Определяем имя поля статуса
            if issue_type in ("Пользовательская история", "Техническая история"):
                status_field = "_Статус истории"
            else:
                status_field = "_Статус задачи"

            last_timestamp_ms = int(max_ts.timestamp() * 1000) if max_ts else 0

            fetch_params = {
                "base_url": base_url,
                "token": token,
                "issue_id": issue_id,
                "status_field_name": status_field,
                "last_timestamp_ms": last_timestamp_ms,
            }

            start_time = time.time()
            try:
                # Вызываем UpdateSingleIssueHistoryAction с тем же транзакционным контекстом
                single_result = single_action.run(tx_ctx, fetch_params)
                inserted = single_result.get("inserted", 0)
                events_fetched = single_result.get("events_fetched", 0)

                total_inserted += inserted
                total_processed += 1
                batch_counter += 1

                elapsed = time.time() - start_time
                logger.info(f"[{idx}/{len(issues)}] Задача {issue_id}: вставлено {inserted} событий, обработано за {elapsed:.2f}с")

                details[issue_id] = {
                    "inserted": inserted,
                    "events_fetched": events_fetched,
                    "elapsed": elapsed,
                    "status_field": status_field,
                }

            except Exception as e:
                logger.error(f"Ошибка при обработке задачи {issue_id}: {e}")
                total_failed += 1
                details[issue_id] = {"error": str(e)}
                # Транзакция может быть в состоянии ошибки, но мы её не откатываем,
                # так как savepoint не используется. При ошибке внутри UpdateSingleIssueHistoryAction
                # транзакция будет помечена как abort, и последующие команды будут игнорироваться.
                # Чтобы продолжить, нужно либо делать rollback и начинать новую транзакцию,
                # либо использовать savepoint. В данном случае без savepoint при ошибке одной задачи
                # вся транзакция становится неработоспособной, поэтому мы должны прервать обработку.
                # Для надёжности стоит либо добавить savepoint внутри цикла, либо коммитить после каждой успешной задачи.
                # Пока реализуем простой вариант: при любой ошибке прекращаем обработку.
                # Можно позже улучшить, добавив savepoint.
                # Прерываем цикл, но перед этим нужно откатить транзакцию.
                conn.rollback()
                logger.error("Обработка прервана из-за ошибки. Транзакция откачена.")
                break

            # Пакетный коммит после каждых BATCH_SIZE успешных задач
            if batch_counter >= BATCH_SIZE:
                conn.commit()
                logger.info(f"Промежуточный коммит после {batch_counter} задач")
                batch_counter = 0

        # Финальный коммит оставшихся
        if batch_counter > 0:
            conn.commit()
            logger.info(f"Финальный коммит после {batch_counter} задач")

        return {
            "total_issues_processed": total_processed,
            "total_events_inserted": total_inserted,
            "total_issues_skipped": total_skipped,
            "total_issues_failed": total_failed,
            "details": details,
        }

    @IntFieldChecker("total_issues_processed", min_value=0)
    @IntFieldChecker("total_events_inserted", min_value=0)
    @IntFieldChecker("total_issues_skipped", min_value=0)
    @IntFieldChecker("total_issues_failed", min_value=0)
    @InstanceOfChecker("details", expected_class=dict)
    def _postHandleAspect(self, ctx: Context, params: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        # Уже закоммитили внутри цикла, но на всякий случай закроем менеджер
        for mgr in result.get("managers", []):
            mgr.commit()
        result.pop("managers", None)
        result.pop("tx_ctx", None)
        return result

    def _onErrorAspect(self, ctx: Context, params: Dict[str, Any], result: Dict[str, Any], error: Exception) -> None:
        logger.error(f"Ошибка в UpdateAllIssuesHistoryAction: {error}")
        for mgr in result.get("managers", []):
            mgr.rollback()