#!/usr/bin/env python3
import sys
import os
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from YouTrackMCP import YouTrackMCPServer

def main():
    snapshot_date = date.today()
    result = YouTrackMCPServer.bulk_youtrack_issue_to_postgres(
        project_id="OPD_IPPM",
        page_size=100,
        snapshot_date=snapshot_date
    )
    if result["success"]:
        print("✅ Успех:", result["result"])
    else:
        print("❌ Ошибки:", result["errors"])

if __name__ == "__main__":
    main()