#!/usr/bin/env python3
# Utils/test_find_issues.py
"""
Простой тест для FindIssuesNeedingHistoryUpdateAction.
Запрашивает первую страницу задач, обновлённых после указанной даты,
с возможностью фильтрации по проекту.
"""

import sys
import os
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

# Добавляем корень проекта в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

from ActionEngine import UserInfo, Context
from APP.FindIssuesNeedingHistoryUpdateAction import FindIssuesNeedingHistoryUpdateAction

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


def main():
    # Проверяем обязательные переменные
    required_vars = ["YOUTRACK_URL", "YOUTRACK_TOKEN"]
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        print(f"❌ Отсутствуют переменные окружения: {', '.join(missing)}")
        sys.exit(1)

    base_url = os.getenv("YOUTRACK_URL")
    token = os.getenv("YOUTRACK_TOKEN")

    # Настройки теста
    page_size = 50                     # сколько задач на странице
    since_days = 1                     # ищем задачи, обновлённые за последние N дней
    since_timestamp_ms = int((datetime.utcnow() - timedelta(days=since_days)).timestamp() * 1000)

    # Если нужно отфильтровать по проекту, укажите его ключ (например, "OPD_IPPM")
    # project_id = "OPD_IPPM"
    project_id = None   # или None для всех проектов

    # Создаём контекст (пользователь тестовый)
    user_info = UserInfo(user_id="test_finder", roles=["user"])
    ctx = Context(user=user_info)

    # Параметры для действия
    params = {
        "base_url": base_url,
        "token": token,
        "page_size": page_size,
        "since_timestamp_ms": since_timestamp_ms,
        "project_id": "OPD_IPPM"
    }   

    action = FindIssuesNeedingHistoryUpdateAction()
    try:
        result = action.run(ctx, params)
        issues = result.get("issues", [])
        print(f"\n✅ Найдено задач: {len(issues)}")
        if issues:
            # Выводим первые несколько ID для наглядности
            print("Первые 10 ID задач:")
            for i, issue in enumerate(issues[:10], 1):
                print(f"  {i}. {issue['id']}")
        # Полный вывод в JSON
        print("\nПолный результат:")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()