# Utils/test_fetch_history.py
#!/usr/bin/env python3
"""
Тестовый скрипт для FetchIssueStatusHistoryAction.
Запрашивает историю статусов для указанной задачи и выводит результат.
"""

import sys
import os
import json
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Добавляем корень проекта в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

from ActionEngine import UserInfo, Context, TransactionContext, PostgresConnectionManager
from APP.FetchIssueStatusHistoryAction import FetchIssueStatusHistoryAction

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True
)

def main():
    # Проверяем наличие обязательных переменных окружения
    required_vars = ["YOUTRACK_URL", "YOUTRACK_TOKEN", "POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD"]
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        print(f"❌ Отсутствуют переменные окружения: {', '.join(missing)}")
        sys.exit(1)

    # ID задачи для теста (можно передать аргументом командной строки)
    if len(sys.argv) > 1:
        issue_id = sys.argv[1]
    else:
        issue_id = "OPD_IPPM-1067"  # задача с известной историей

    # Создаём контекст с тестовым пользователем
    user_info = UserInfo(user_id="test", roles=["user"])
    ctx = Context(user=user_info)

    # Параметры подключения к БД
    db_params = {
        "host": os.getenv("POSTGRES_HOST"),
        "port": int(os.getenv("POSTGRES_PORT", "5432")),
        "dbname": os.getenv("POSTGRES_DB"),
        "user": os.getenv("POSTGRES_USER"),
        "password": os.getenv("POSTGRES_PASSWORD"),
    }

    # Открываем соединение с БД (нужно для сохранения, даже если мы не будем сохранять, но действие требует контекст)
    mgr = PostgresConnectionManager(db_params)
    mgr.open()
    tx_ctx = TransactionContext(
        user=ctx.user,
        request=ctx.request,
        environment=ctx.environment,
        connection=mgr.connection
    )

    # Параметры для действия
    params = {
        "base_url": os.getenv("YOUTRACK_URL"),
        "token": os.getenv("YOUTRACK_TOKEN"),
        "issue_id": issue_id,
        # "from_timestamp_ms": None  # можно задать, если нужно
    }

    action = FetchIssueStatusHistoryAction()
    try:
        result = action.run(tx_ctx, params)
        print(f"\n✅ Результат для задачи {issue_id}:")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        mgr.commit()  # фиксируем транзакцию (если были вставки)
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        mgr.rollback()
    finally:
        # Закрываем соединение (уже сделано в commit/rollback)
        pass

if __name__ == "__main__":
    main()