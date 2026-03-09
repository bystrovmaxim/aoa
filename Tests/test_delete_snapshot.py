# Utils/test_delete_snapshot.py

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
    user_info = UserInfo(user_id="test", roles=["admin"])
    ctx = Context(user=user_info)

    result = YouTrackEntryPoint.delete_snapshot(
        ctx=ctx,
        snapshot_date=date.today(),
        tables=["user_tech_stories", "taskitems"],
        schema="youtrack"
    )
    print(json.dumps(result, ensure_ascii=False))

if __name__ == "__main__":
    main()