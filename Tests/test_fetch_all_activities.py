#!/usr/bin/env python3
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

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def datetime_serializer(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

def main():
    issue_id = sys.argv[1] if len(sys.argv) > 1 else "2-115777"
    base_url = os.getenv("YOUTRACK_URL")
    token = os.getenv("YOUTRACK_TOKEN")
    if not base_url or not token:
        print("❌ Нет YOUTRACK_URL или YOUTRACK_TOKEN")
        sys.exit(1)

    ctx = Context(user=UserInfo(user_id="test", roles=["user"]))
    action = FetchIssueAllActivitiesAction()

    params = {
        "base_url": base_url,
        "token": token,
        "issue_id": issue_id,
        "categories": [
            "CustomFieldCategory",
            "CommentsCategory",
            "AttachmentsCategory",
            "IssueCreatedCategory",
            "LinksCategory"
        ],
    }

    try:
        result = action.run(ctx, params)
        print(json.dumps(result, indent=2, default=datetime_serializer, ensure_ascii=False))
    except Exception as e:
        logging.exception("Ошибка при выполнении действия")
        print(f"❌ Ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()