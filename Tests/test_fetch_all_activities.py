#!/usr/bin/env python3
# Tests/test_fetch_all_activities.py

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
from APP.FetchIssueAllActivitiesAction import FetchIssueAllActivitiesAction

logging.basicConfig(level=logging.INFO)

def datetime_serializer(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

def main():
    if len(sys.argv) > 1:
        issue_id = sys.argv[1]
    else:
        issue_id = "2-115777"  # замените на существующий ID

    base_url = os.getenv("YOUTRACK_URL")
    token = os.getenv("YOUTRACK_TOKEN")
    if not base_url or not token:
        print("❌ Нет YOUTRACK_URL или YOUTRACK_TOKEN")
        sys.exit(1)

    ctx = Context(user=UserInfo(user_id="test", roles=["user"]))
    action = FetchIssueAllActivitiesAction()

    # Список категорий для запроса (можно уточнить под вашу версию YouTrack)
    categories = [
        "CustomFieldCategory",
        #"CommentsCategory",
        #"AttachmentsCategory",
        #"IssueCreatedCategory",
        #"LinksCategory"
    ]

    params = {
        "base_url": base_url,
        "token": token,
        "issue_id": issue_id,
        "categories": categories,
        # "from_timestamp_ms": 1234567890000  # опционально
    }
    try:
        result = action.run(ctx, params)
        print(json.dumps(result, indent=2, default=datetime_serializer, ensure_ascii=False))
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()