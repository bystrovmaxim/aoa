# Utils/test_fetch_history.py
import sys
import os
import json
import logging
from datetime import datetime, date
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

from ActionEngine import UserInfo, Context
from APP.FetchIssueStatusHistoryAction import FetchIssueStatusHistoryAction

# Настройка логирования
logging.basicConfig(level=logging.INFO)

def datetime_serializer(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

def main():
    issue_id = "2-115777"  # или можно передать аргументом
    base_url = os.getenv("YOUTRACK_URL")
    token = os.getenv("YOUTRACK_TOKEN")
    if not base_url or not token:
        print("❌ Нет YOUTRACK_URL или YOUTRACK_TOKEN")
        return

    ctx = Context(user=UserInfo(user_id="test", roles=["user"]))
    action = FetchIssueStatusHistoryAction()
    params = {
        "base_url": base_url,
        "token": token,
        "issue_id": issue_id,
    }
    try:
        result = action.run(ctx, params)
        print(json.dumps(result, indent=2, default=datetime_serializer, ensure_ascii=False))
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    main()