#!/usr/bin/env python3
# Tests/test_update_single_issue_history.py

import sys
import os
import json
import logging
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

from ActionEngine import UserInfo, Context, TransactionContext, PostgresConnectionManager
from APP.UpdateSingleIssueHistoryAction import UpdateSingleIssueHistoryAction

logging.basicConfig(level=logging.INFO)


def main():
    # Проверяем обязательные переменные окружения
    required_vars = [
        "YOUTRACK_URL", "YOUTRACK_TOKEN",
        "POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD"
    ]
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        print(f"❌ Отсутствуют переменные окружения: {', '.join(missing)}")
        sys.exit(1)

    # Параметры задачи (можно передать аргументом командной строки)
    issue_id = sys.argv[1] if len(sys.argv) > 1 else "2-115777"  # замените на существующий ID

    base_url = os.getenv("YOUTRACK_URL")
    token = os.getenv("YOUTRACK_TOKEN")
    status_field = "_Статус истории"  # или другое имя поля

    # Параметры подключения к БД
    db_params = {
        "host": os.getenv("POSTGRES_HOST"),
        "port": int(os.getenv("POSTGRES_PORT", "5432")),
        "dbname": os.getenv("POSTGRES_DB"),
        "user": os.getenv("POSTGRES_USER"),
        "password": os.getenv("POSTGRES_PASSWORD"),
    }

    # Создаём контекст пользователя
    user_info = UserInfo(user_id="test_single", roles=["user"])
    ctx = Context(user=user_info)

    # Открываем соединение с БД и создаём транзакционный контекст
    mgr = PostgresConnectionManager(db_params)
    mgr.open()
    tx_ctx = TransactionContext(
        user=ctx.user,
        request=ctx.request,
        environment=ctx.environment,
        connection=mgr.connection
    )

    action = UpdateSingleIssueHistoryAction()
    params = {
        "base_url": base_url,
        "token": token,
        "issue_id": issue_id,
        "status_field_name": status_field,
        "last_timestamp_ms": 0  # добавлен обязательный параметр
    }

    try:
        result = action.run(tx_ctx, params)
        mgr.commit()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        mgr.rollback()
        print(f"❌ Ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()