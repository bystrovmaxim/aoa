#!/usr/bin/env python3
import sys
import os

# Добавляем корневую папку проекта в путь поиска модулей
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from YouTrackMCP import YouTrackMCPServer
from ActionEngine.Context import Context

def main():
    ctx = Context(user_id="test", roles=["user"])
    result = YouTrackMCPServer.fetch_issues_to_csv(
        ctx=ctx,
        base_url=os.getenv("YOUTRACK_URL", "https://youtrack.brusnika.tech"),
        token=os.getenv("YOUTRACK_TOKEN"),
        output_file="/tmp/issues.csv"
    )
    if result["success"]:
        print("✅ Успех:", result["result"])
    else:
        print("❌ Ошибки:", result["errors"])

if __name__ == "__main__":
    main()