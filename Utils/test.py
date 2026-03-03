#!/usr/bin/env python3
import sys
import os

# Добавляем корневую папку проекта в путь поиска модулей
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from YouTrackMCP import YouTrackMCPServer

def main():
    result = YouTrackMCPServer.bulk_youtrack_issue_to_csv(
        base_url=os.getenv("YOUTRACK_URL", "https://youtrack.brusnika.tech"),
        token=os.getenv("YOUTRACK_TOKEN"),
        user_stories_file="/tmp/user_stories.csv",
        tasks_file="/tmp/tasks.csv",
        page_size=100,
        project_id="OPD_IPPM"
    )
    if result["success"]:
        print("✅ Успех:", result["result"])
    else:
        print("❌ Ошибки:", result["errors"])

if __name__ == "__main__":
    main()