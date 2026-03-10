# Utils/test_youtrack_issue_to_postgres.py
"""
Тестовый скрипт для выгрузки снимков в PostgreSQL.
Создаёт минимальный контекст и вызывает фасад.
"""

import sys
import os
import json
from datetime import date
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

from ActionEngine import UserInfo, Context
from EntryPoint.YouTrackEntryPoint import YouTrackEntryPoint


def main():
    # Создаём контекст с тестовым пользователем (роль user)
    user_info = UserInfo(user_id="test", roles=["user"])
    ctx = Context(user=user_info)

    # Вызываем метод фасада
    result = YouTrackEntryPoint.bulk_youtrack_issue_to_postgres(
        ctx=ctx,
        #project_id="OPD_IPPM",
        page_size=5000,
        snapshot_date=date.today() # date.fromisoformat("2026-03-05") date.today()
    )
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()