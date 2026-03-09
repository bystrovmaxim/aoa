# Utils/test_youtrack_issue_to_csv.py
"""
Тестовый скрипт для выгрузки задач в CSV.
Создаёт минимальный контекст и вызывает фасад.
"""

import sys
import os
import json
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
    result = YouTrackEntryPoint.bulk_youtrack_issue_to_csv(
        ctx=ctx,
        user_stories_file="/tmp/user_stories.csv",
        tasks_file="/tmp/tasks.csv",
        page_size=100,
        project_id="OPD_IPPM"
    )
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()