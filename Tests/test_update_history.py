# Utils/test_update_history.py
import sys
import os
import json
import logging
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

from ActionEngine import UserInfo, Context
from APP.UpdateAllIssuesHistoryAction import UpdateAllIssuesHistoryAction

logging.basicConfig(level=logging.INFO)
logging.getLogger("APP.FindIssuesNeedingHistoryUpdateAction").setLevel(logging.WARNING)
logging.getLogger("APP.FetchIssueStatusHistoryAction").setLevel(logging.WARNING)


def main():
    required_vars = [
        "YOUTRACK_URL", "YOUTRACK_TOKEN",
        "POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD"
    ]
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        print(f"❌ Отсутствуют переменные окружения: {', '.join(missing)}")
        sys.exit(1)

    user_info = UserInfo(user_id="history_updater", roles=["user"])
    ctx = Context(user=user_info)

    # Параметры для действия
    params = {
        "base_url": os.getenv("YOUTRACK_URL"),
        "token": os.getenv("YOUTRACK_TOKEN"),
        "page_size": 1000,
        # Можно передать один проект:
        #"project_code": "INF", #"OPD_IPPM",
        # Или несколько проектов:
        #"project_code": ["AI", "INF"],
        # Или не указывать project_code для обработки всех проектов из БД.
        "pg_host": os.getenv("POSTGRES_HOST"),
        "pg_port": int(os.getenv("POSTGRES_PORT", "5432")),
        "pg_db": os.getenv("POSTGRES_DB"),
        "pg_user": os.getenv("POSTGRES_USER"),
        "pg_password": os.getenv("POSTGRES_PASSWORD"),
    }

    action = UpdateAllIssuesHistoryAction()
    try:
        result = action.run(ctx, params)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()