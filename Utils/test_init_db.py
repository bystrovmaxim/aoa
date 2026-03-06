# Utils/test_init_db.py
"""
Тестовый скрипт для инициализации базы данных.
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
    # Создаём контекст с тестовым пользователем (роль admin)
    user_info = UserInfo(user_id="test", roles=["admin_db"])
    ctx = Context(user=user_info)

    # Вызываем метод фасада
    result = YouTrackEntryPoint.init_database(ctx)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()